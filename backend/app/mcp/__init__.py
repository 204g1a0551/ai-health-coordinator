"""
Model Context Protocol (MCP) Integration Module.
Provides standardized tool definitions, client, and servers for external healthcare services.
"""

from app.mcp.models import MCPTool, MCPToolCall, MCPToolResult, MCPAuditLog
from app.mcp.client import mcp_client
from app.mcp.registry import mcp_registry

__all__ = [
    "MCPTool",
    "MCPToolCall",
    "MCPToolResult",
    "MCPAuditLog",
    "mcp_client",
    "mcp_registry",
]
