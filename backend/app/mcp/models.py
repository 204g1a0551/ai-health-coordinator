"""
MCP Models & Schemas
Standard definitions for tools, invocations, results, and audit logs.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    name: str = Field(..., description="Unique tool name within the server")
    description: str = Field(..., description="Clear explanation of the tool capability")
    input_schema: Dict[str, Any] = Field(..., description="JSON Schema for tool input arguments")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="Schema for tool output result")
    timeout_seconds: float = Field(default=5.0, description="Execution timeout in seconds")
    requires_auth: bool = Field(default=False, description="Whether this tool requires an authenticated user")
    allowed_agents: List[str] = Field(default_factory=list, description="Agents authorized to invoke this tool")
    cache_ttl_seconds: Optional[int] = Field(default=None, description="Redis cache TTL if idempotent")


class MCPToolCall(BaseModel):
    server_name: str = Field(..., description="Target MCP server identifier")
    tool_name: str = Field(..., description="Target tool name")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input parameters")
    caller_agent: str = Field(default="unknown", description="Identifier of calling agent")
    session_id: Optional[str] = Field(default=None, description="Chat session ID")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID")
    request_id: Optional[str] = Field(default=None, description="Unique trace request ID")


class MCPToolResult(BaseModel):
    success: bool = Field(..., description="Whether tool execution completed successfully")
    data: Optional[Any] = Field(default=None, description="Structured tool payload")
    error: Optional[str] = Field(default=None, description="Sanitized, user-safe error message")
    error_code: Optional[str] = Field(default=None, description="Machine-readable error code")
    execution_time_ms: float = Field(default=0.0, description="Duration in milliseconds")
    cached: bool = Field(default=False, description="Whether result was served from cache")
    source: Optional[str] = Field(default=None, description="Originating provider or dataset source")
    timestamp: str = Field(default="", description="UTC timestamp of completion")


class MCPAuditLog(BaseModel):
    id: str = Field(..., description="Unique log identifier")
    timestamp: str = Field(..., description="ISO/Readable UTC timestamp")
    agent: str = Field(..., description="Calling agent name")
    server: str = Field(..., description="MCP server name")
    tool: str = Field(..., description="Tool name executed")
    request_id: str = Field(..., description="Request trace ID")
    duration_ms: float = Field(..., description="Total execution time")
    status: str = Field(..., description="SUCCESS, FAILED, TIMEOUT, UNAUTHORIZED, or VALIDATION_ERROR")
    source: Optional[str] = Field(default=None, description="Data source name")
    cached: bool = Field(default=False, description="Was served from Redis cache")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
