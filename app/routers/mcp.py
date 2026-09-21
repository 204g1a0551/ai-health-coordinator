"""
MCP Observability & Administration Router
Provides endpoints for monitoring MCP tool execution, audit logs, and tool schemas.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field

from app.mcp.client import mcp_client
from app.mcp.registry import mcp_registry
from app.mcp.models import MCPAuditLog, MCPToolResult

router = APIRouter(prefix="/api/mcp", tags=["Model Context Protocol (MCP)"])


class ToolInvocationRequest(BaseModel):
    server: str = Field(..., description="Target MCP server name (e.g. doctor_mcp, medicine_mcp)")
    tool: str = Field(..., description="Tool name to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    caller_agent: str = Field(default="admin_tester", description="Calling agent identity")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    user_id: Optional[str] = Field(default=None, description="User ID")


@router.get("/servers")
def list_mcp_servers():
    """Returns all registered in-process MCP servers and high-level descriptions."""
    return {
        "servers": mcp_registry.list_servers(),
        "total_servers": len(mcp_registry.list_servers()),
        "status": "operational",
    }


@router.get("/tools")
def list_mcp_tools(server: Optional[str] = Query(default=None, description="Filter tools by server name")):
    """Returns all registered MCP tools, input schemas, timeouts, and authorization rules."""
    tools = mcp_registry.list_tools(server_name=server)
    return {
        "server_filter": server,
        "tools": tools,
        "total_tools": len(tools),
    }


@router.get("/audit-logs", response_model=List[MCPAuditLog])
def get_mcp_audit_logs(
    limit: int = Query(default=50, ge=1, le=500, description="Max logs to return"),
    server: Optional[str] = Query(default=None, description="Filter by server name"),
    agent: Optional[str] = Query(default=None, description="Filter by calling agent"),
    status: Optional[str] = Query(default=None, description="Filter by status (SUCCESS, FAILED, etc.)"),
):
    """
    Developer / Admin observability log stream.
    Exposes tool execution duration, timestamp, server, calling agent, and status.
    PII and patient health details are strictly redacted.
    """
    return mcp_client.get_audit_logs(limit=limit, server=server, agent=agent, status=status)


@router.post("/tools/call", response_model=MCPToolResult)
def execute_mcp_tool(req: ToolInvocationRequest):
    """
    Controlled tool invocation endpoint for integration testing and developer diagnostics.
    Enforces authorization, input schema validation, rate-limits, and audit logging.
    """
    result = mcp_client.call_tool(
        server_name=req.server,
        tool_name=req.tool,
        arguments=req.arguments,
        caller_agent=req.caller_agent,
        session_id=req.session_id,
        user_id=req.user_id,
    )
    return result
