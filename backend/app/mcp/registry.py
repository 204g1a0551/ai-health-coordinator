"""
MCP Central Registry
Manages registered MCP servers, tool discovery, and agent access authorization policies.
"""

from typing import Any, Dict, List, Optional
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.mcp.doctor_server import doctor_mcp_server
from app.mcp.appointment_server import appointment_mcp_server
from app.mcp.pharmacy_server import pharmacy_mcp_server
from app.mcp.medicine_server import medicine_mcp_server
from app.mcp.document_server import document_mcp_server
from app.mcp.insurance_server import insurance_mcp_server
from app.mcp.emergency_server import emergency_mcp_server


class MCPRegistry:
    def __init__(self):
        self._servers: Dict[str, BaseMCPServer] = {}
        self._init_default_servers()

    def _init_default_servers(self):
        self.register_server(doctor_mcp_server)
        self.register_server(appointment_mcp_server)
        self.register_server(pharmacy_mcp_server)
        self.register_server(medicine_mcp_server)
        self.register_server(document_mcp_server)
        self.register_server(insurance_mcp_server)
        self.register_server(emergency_mcp_server)

    def register_server(self, server: BaseMCPServer):
        self._servers[server.name] = server

    def get_server(self, name: str) -> Optional[BaseMCPServer]:
        return self._servers.get(name)

    def list_servers(self) -> List[Dict[str, str]]:
        return [
            {"name": s.name, "description": s.description, "tools_count": len(s.list_tools())}
            for s in self._servers.values()
        ]

    def list_tools(self, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        servers = [self._servers[server_name]] if server_name and server_name in self._servers else self._servers.values()
        for s in servers:
            for t in s.list_tools():
                results.append({
                    "server": s.name,
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                    "timeout_seconds": t.timeout_seconds,
                    "allowed_agents": t.allowed_agents,
                })
        return results

    def is_agent_authorized(self, agent_name: str, server_name: str, tool_name: str) -> bool:
        """
        Verifies if the specified calling agent is authorized to invoke this tool.
        Administrative, system, or supervisor agents have broad routing permissions.
        """
        # Super-agents with system clearance
        if agent_name in ["supervisor", "admin", "system"]:
            return True

        server = self.get_server(server_name)
        if not server:
            return False

        tool = server.get_tool(tool_name)
        if not tool:
            return False

        if not tool.allowed_agents:
            return True

        return agent_name in tool.allowed_agents

    def get_tools_for_agent(self, agent_name: str) -> List[MCPTool]:
        """Returns all tools the agent is authorized to use."""
        authorized_tools = []
        for s in self._servers.values():
            for t in s.list_tools():
                if self.is_agent_authorized(agent_name, s.name, t.name):
                    authorized_tools.append(t)
        return authorized_tools


mcp_registry = MCPRegistry()
