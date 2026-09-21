"""
Doctor/Provider MCP Server
Exposes standardized healthcare provider search and facility tools.
"""

from typing import Any, Dict, List, Optional
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.services.provider_service import provider_service


class DoctorMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="doctor_mcp",
            description="Provider Directory & Doctor Discovery MCP Server for clinics, specialists, and hospitals",
        )
        self._register_doctor_tools()

    def _register_doctor_tools(self):
        # 1. search_doctors
        self.register_tool(
            MCPTool(
                name="search_doctors",
                description="Search verified doctors matching department, locality/location, or keyword query",
                input_schema={
                    "type": "object",
                    "properties": {
                        "department": {"type": "string", "description": "Medical specialty/department (e.g. ENT, Cardiology)"},
                        "location": {"type": "string", "description": "Locality or city area (e.g. Whitefield, Indiranagar)"},
                        "query": {"type": "string", "description": "Doctor name or specialty keyword"},
                    },
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_doctors,
        )

        # 2. search_by_department
        self.register_tool(
            MCPTool(
                name="search_by_department",
                description="Find doctors specializing in a specific clinical department",
                input_schema={
                    "type": "object",
                    "properties": {
                        "department": {"type": "string", "description": "Clinical department name"},
                        "location": {"type": "string", "description": "Optional locality filter"},
                    },
                    "required": ["department"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_by_department,
        )

        # 3. search_by_location
        self.register_tool(
            MCPTool(
                name="search_by_location",
                description="Find doctors and clinics within a specific geographic locality",
                input_schema={
                    "type": "object",
                    "properties": {
                        "location": {"type": "string", "description": "Locality name"},
                        "department": {"type": "string", "description": "Optional medical department filter"},
                    },
                    "required": ["location"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_by_location,
        )

        # 4. get_doctor_details
        self.register_tool(
            MCPTool(
                name="get_doctor_details",
                description="Retrieve complete profile, experience, clinic, and credentials of a doctor",
                input_schema={
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "string", "description": "Unique doctor identifier"},
                    },
                    "required": ["doctor_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_doctor_details,
        )

        # 5. search_hospitals
        self.register_tool(
            MCPTool(
                name="search_hospitals",
                description="Search hospitals, multi-specialty medical centers, and clinics",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Hospital name or keyword"},
                        "location": {"type": "string", "description": "Area or neighborhood"},
                    },
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_search_hospitals,
        )

        # 6. get_hospital_details
        self.register_tool(
            MCPTool(
                name="get_hospital_details",
                description="Retrieve detailed facilities, departments, and location of a hospital",
                input_schema={
                    "type": "object",
                    "properties": {
                        "hospital_id": {"type": "string", "description": "Unique hospital identifier"},
                    },
                    "required": ["hospital_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_hospital_details,
        )

    # --------------------------------------------------------------------------
    # Tool Handlers
    # --------------------------------------------------------------------------
    def _handle_search_doctors(
        self,
        department: Optional[str] = None,
        location: Optional[str] = None,
        query: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = provider_service.search_doctors(
            query=query,
            department=department,
            locality=location,
        )
        if not results and department:
            results = provider_service.search_by_department(department=department)
        if not results and location:
            results = provider_service.search_by_location(locality=location)

        return {
            "doctors": results,
            "total_found": len(results),
            "source": provider_service.provider.provider_name,
        }

    def _handle_search_by_department(
        self,
        department: str,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = provider_service.search_by_department(
            department=department,
            locality=location,
        )
        return {
            "department": department,
            "doctors": results,
            "total_found": len(results),
            "source": provider_service.provider.provider_name,
        }

    def _handle_search_by_location(
        self,
        location: str,
        department: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = provider_service.search_by_location(
            locality=location,
            department=department,
        )
        return {
            "location": location,
            "doctors": results,
            "total_found": len(results),
            "source": provider_service.provider.provider_name,
        }

    def _handle_get_doctor_details(self, doctor_id: str) -> Dict[str, Any]:
        details = provider_service.get_doctor_details(doctor_id=doctor_id)
        if not details:
            return {"found": False, "doctor": None, "error": f"Doctor '{doctor_id}' not found"}
        return {
            "found": True,
            "doctor": details,
            "source": provider_service.provider.provider_name,
        }

    def _handle_search_hospitals(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        results = provider_service.search_hospitals(query=query, locality=location)
        return {
            "hospitals": results,
            "total_found": len(results),
            "source": provider_service.provider.provider_name,
        }

    def _handle_get_hospital_details(self, hospital_id: str) -> Dict[str, Any]:
        hospitals = provider_service.search_hospitals()
        for h in hospitals:
            if h.get("id") == hospital_id:
                return {"found": True, "hospital": h, "source": provider_service.provider.provider_name}
        return {"found": False, "hospital": None, "error": f"Hospital '{hospital_id}' not found"}


doctor_mcp_server = DoctorMCPServer()
