"""
MCP Client Layer
Handles standardized tool invocation, agent authorization, schema validation,
caching, execution timeouts, error sanitization, and audit logging.
"""

import time
import uuid
import logging
import concurrent.futures
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

from app.mcp.models import MCPToolCall, MCPToolResult, MCPAuditLog
from app.mcp.registry import mcp_registry
from app.mcp.base_server import MCPValidationError
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


class MCPClient:
    """
    Standard Model Context Protocol client for Agentic AI workflows.
    Ensures safe, authorized, and observable tool invocations across all healthcare servers.
    """

    def __init__(self):
        self.registry = mcp_registry
        self._audit_logs: List[MCPAuditLog] = []
        self._max_audit_logs = 1000
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

    def _sanitize_for_audit(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Redacts sensitive PII and medical payload text from audit logs."""
        safe_copy = {}
        for k, v in arguments.items():
            if k in ["patient_name", "patient_phone", "raw_text", "text"]:
                safe_copy[k] = "[REDACTED_FOR_PRIVACY]"
            else:
                safe_copy[k] = v
        return safe_copy

    def _log_audit(
        self,
        request_id: str,
        agent: str,
        server: str,
        tool: str,
        duration_ms: float,
        status: str,
        source: Optional[str] = None,
        cached: bool = False,
        error_message: Optional[str] = None,
    ) -> None:
        """Records execution metadata to in-memory observability buffer."""
        log_entry = MCPAuditLog(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.utcnow().strftime("%H:%M:%S"),
            agent=agent,
            server=server,
            tool=tool,
            request_id=request_id,
            duration_ms=duration_ms,
            status=status,
            source=source,
            cached=cached,
            error_message=error_message,
        )
        self._audit_logs.append(log_entry)
        if len(self._audit_logs) > self._max_audit_logs:
            self._audit_logs.pop(0)

        logger.info(
            f"MCP Audit: [{log_entry.timestamp}] agent={agent} server={server} tool={tool} "
            f"duration={duration_ms}ms status={status} cached={cached}"
        )

    def get_audit_logs(
        self,
        limit: int = 100,
        server: Optional[str] = None,
        agent: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[MCPAuditLog]:
        """Retrieve recent audit logs with optional filtering for developer/admin view."""
        logs = list(reversed(self._audit_logs))
        if server:
            logs = [l for l in logs if l.server.lower() == server.lower()]
        if agent:
            logs = [l for l in logs if l.agent.lower() == agent.lower()]
        if status:
            logs = [l for l in logs if l.status.lower() == status.lower()]
        return logs[:limit]

    def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        caller_agent: str = "unknown",
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> MCPToolResult:
        """
        Executes an approved MCP tool with security controls:
        1. Agent Authorization check
        2. Schema and Parameter Validation
        3. Redis Cache check (for read-only idempotent queries)
        4. Timeout Enforcement
        5. Sanitized Error Handling
        6. Observability Audit Logging
        """
        start_time = time.time()
        request_id = str(uuid.uuid4())[:8]
        args = dict(arguments or {})
        now_ts = datetime.utcnow().isoformat() + "Z"

        server = self.registry.get_server(server_name)
        if not server:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "FAILED", error_message=f"Server '{server_name}' not found")
            return MCPToolResult(
                success=False,
                error=f"Healthcare service '{server_name}' is currently unavailable.",
                error_code="SERVER_NOT_FOUND",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )

        tool = server.get_tool(tool_name)
        if not tool:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "FAILED", error_message=f"Tool '{tool_name}' not found")
            return MCPToolResult(
                success=False,
                error=f"Requested operation '{tool_name}' is not supported.",
                error_code="TOOL_NOT_FOUND",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )

        # 1. Authorization Verification
        if not self.registry.is_agent_authorized(caller_agent, server_name, tool_name):
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "UNAUTHORIZED", error_message="Unauthorized agent call")
            return MCPToolResult(
                success=False,
                error=f"Access denied: Agent '{caller_agent}' is not authorized to invoke '{tool_name}'.",
                error_code="UNAUTHORIZED_TOOL_ACCESS",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )

        # 2. Redis Caching Check (if configured and idempotent)
        cache_key = None
        if tool.cache_ttl_seconds and tool.cache_ttl_seconds > 0:
            serialized_args = json.dumps(args, sort_keys=True)
            cache_key = f"mcp_cache:{server_name}:{tool_name}:{serialized_args}"
            cached_data = redis_service.get_cached_healthcare_data(cache_key)
            if cached_data is not None:
                duration_ms = round((time.time() - start_time) * 1000, 2)
                self._log_audit(
                    request_id, caller_agent, server_name, tool_name, duration_ms, "SUCCESS",
                    source=cached_data.get("source") if isinstance(cached_data, dict) else None,
                    cached=True
                )
                return MCPToolResult(
                    success=True,
                    data=cached_data,
                    cached=True,
                    source=cached_data.get("source") if isinstance(cached_data, dict) else None,
                    execution_time_ms=duration_ms,
                    timestamp=now_ts,
                )

        # 3. Execution with Timeout Control
        context = {
            "session_id": session_id or args.get("session_id"),
            "user_id": user_id or args.get("user_id"),
            "request_id": request_id,
            "caller_agent": caller_agent,
        }

        timeout_sec = tool.timeout_seconds or 5.0

        try:
            future = self._executor.submit(server.execute_tool, tool_name, args, context)
            raw_result = future.result(timeout=timeout_sec)

            duration_ms = round((time.time() - start_time) * 1000, 2)
            source_label = raw_result.get("source") if isinstance(raw_result, dict) else None

            # Store in Redis cache if applicable
            if cache_key and tool.cache_ttl_seconds:
                redis_service.set_cached_healthcare_data(cache_key, raw_result, ttl=tool.cache_ttl_seconds)

            self._log_audit(
                request_id, caller_agent, server_name, tool_name, duration_ms, "SUCCESS",
                source=source_label, cached=False
            )

            return MCPToolResult(
                success=True,
                data=raw_result,
                source=source_label,
                execution_time_ms=duration_ms,
                cached=False,
                timestamp=now_ts,
            )

        except concurrent.futures.TimeoutError:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "TIMEOUT", error_message="Execution timeout exceeded")
            return MCPToolResult(
                success=False,
                error=f"Operation '{tool_name}' timed out after {timeout_sec}s. Please try again.",
                error_code="TIMEOUT",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )

        except MCPValidationError as ve:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "VALIDATION_ERROR", error_message=str(ve))
            return MCPToolResult(
                success=False,
                error=f"Invalid parameters: {str(ve)}",
                error_code="VALIDATION_ERROR",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )

        except PermissionError as pe:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "UNAUTHORIZED", error_message=str(pe))
            return MCPToolResult(
                success=False,
                error="Access denied: You do not have permission to view this resource.",
                error_code="FORBIDDEN",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"MCP tool execution failed: {tool_name} error={str(e)}", exc_info=True)
            self._log_audit(request_id, caller_agent, server_name, tool_name, duration_ms, "FAILED", error_message=str(e))
            # Never leak raw stack traces or internal secrets to LLM/user
            return MCPToolResult(
                success=False,
                error=f"Healthcare service operation '{tool_name}' is temporarily unavailable. Please try again.",
                error_code="INTERNAL_SERVICE_ERROR",
                execution_time_ms=duration_ms,
                timestamp=now_ts,
            )


mcp_client = MCPClient()
