"""
Pharmacy MCP Server
Controlled tools for pharmacy discovery, location lookup, and verified medicine availability.
"""

from typing import Any, Dict, List, Optional
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.services.pharmacy_service import pharmacy_service, BENGALURU_PHARMACIES


class PharmacyMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="pharmacy_mcp",
            description="Pharmacy Registry & Retailer Discovery MCP Server",
        )
        self._register_pharmacy_tools()

    def _register_pharmacy_tools(self):
        # 1. search_pharmacies
        self.register_tool(
            MCPTool(
                name="search_pharmacies",
                description="Search licensed nearby retail pharmacies by locality, coordinates, and medicine list",
                input_schema={
                    "type": "object",
                    "properties": {
                        "locality": {"type": "string", "description": "Locality name in Bengaluru (e.g. Koramangala, Indiranagar)"},
                        "medicines": {"type": "array", "description": "List of medicine names to check"},
                        "lat": {"type": "number", "description": "User latitude"},
                        "lng": {"type": "number", "description": "User longitude"},
                    },
                },
                allowed_agents=["pharmacy_agent", "medicine_agent", "supervisor", "medicine_search_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_pharmacies,
        )

        # 2. get_pharmacy_details
        self.register_tool(
            MCPTool(
                name="get_pharmacy_details",
                description="Retrieve operational hours, license info, phone, and address of a pharmacy",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pharmacy_id": {"type": "string", "description": "Unique pharmacy store identifier"},
                    },
                    "required": ["pharmacy_id"],
                },
                allowed_agents=["pharmacy_agent", "medicine_agent", "supervisor", "medicine_search_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_pharmacy_details,
        )

        # 3. check_medicine_availability
        self.register_tool(
            MCPTool(
                name="check_medicine_availability",
                description="Check verified pharmacy stocking and location indicator for a medicine",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pharmacy_id": {"type": "string", "description": "Pharmacy store ID"},
                        "medicine_name": {"type": "string", "description": "Medicine name to check"},
                    },
                    "required": ["pharmacy_id", "medicine_name"],
                },
                allowed_agents=["pharmacy_agent", "medicine_agent", "supervisor", "medicine_search_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_check_medicine_availability,
        )

    # --------------------------------------------------------------------------
    # Handlers
    # --------------------------------------------------------------------------
    def _handle_search_pharmacies(
        self,
        locality: Optional[str] = None,
        medicines: Optional[List[str]] = None,
        lat: Optional[float] = None,
        lng: Optional[float] = None,
    ) -> Dict[str, Any]:
        response = pharmacy_service.search_pharmacies(
            medicines=medicines or [],
            locality=locality or "Bengaluru",
            lat=lat,
            lng=lng,
        )
        return response.model_dump() if hasattr(response, "model_dump") else response.dict()

    def _handle_get_pharmacy_details(self, pharmacy_id: str) -> Dict[str, Any]:
        for p in BENGALURU_PHARMACIES:
            if p["id"] == pharmacy_id:
                return {"found": True, "pharmacy": p}
        return {"found": False, "pharmacy": None, "error": f"Pharmacy '{pharmacy_id}' not found"}

    def _handle_check_medicine_availability(self, pharmacy_id: str, medicine_name: str) -> Dict[str, Any]:
        pharmacy = None
        for p in BENGALURU_PHARMACIES:
            if p["id"] == pharmacy_id:
                pharmacy = p
                break
        if not pharmacy:
            return {"found": False, "error": f"Pharmacy '{pharmacy_id}' not found"}

        med_info = pharmacy_service.get_medicine_info(medicine_name)
        return {
            "pharmacy_id": pharmacy_id,
            "pharmacy_name": pharmacy["name"],
            "medicine_name": medicine_name,
            "verified_in_pharmacopoeia": med_info.verified_public_data,
            "stock_indicator": "Retail stock check recommended prior to visit",
            "locality": pharmacy["locality"],
            "contact_phone": pharmacy["phone"],
            "source": "State Pharmacy Council & Pharmacopoeia Reference",
        }


pharmacy_mcp_server = PharmacyMCPServer()
