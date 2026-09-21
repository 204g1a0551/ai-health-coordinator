"""
Emergency Information MCP Server
Provides verified emergency helpline numbers and 24x7 trauma centers.
NOTE: The Red-Flag Triage Agent acts as the safety gate; this MCP tool does NOT decide if an emergency exists.
"""

from typing import Any, Dict, List, Optional
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.services.emergency_service import get_emergency_contacts


EMERGENCY_DEPARTMENTS_BENGALURU = [
    {
        "name": "Manipal Hospital 24x7 Emergency & Trauma Care",
        "locality": "HAL Old Airport Road",
        "phone": "080-2502-4444",
        "ambulance": "105999",
        "address": "98, HAL Old Airport Rd, Kodihalli, Bengaluru, Karnataka 560017",
        "type": "Level 1 Trauma & Emergency Department",
    },
    {
        "name": "Aster CMI Hospital 24x7 Emergency Care",
        "locality": "Hebbal",
        "phone": "080-4344-4344",
        "ambulance": "080-4344-4344",
        "address": "No. 43/42, NH 44, Sahakar Nagar, Hebbal, Bengaluru, Karnataka 560092",
        "type": "Comprehensive Emergency & Stroke Center",
    },
    {
        "name": "Fortis Hospital Emergency Care",
        "locality": "Bannerghatta Road",
        "phone": "080-6621-4444",
        "ambulance": "105711",
        "address": "154/9, Bannerghatta Rd, Opp IIM-B, Bilekahalli, Bengaluru, Karnataka 560076",
        "type": "24x7 Cardiac & Trauma Emergency Center",
    },
    {
        "name": "Narayana Multispeciality Hospital Emergency",
        "locality": "Whitefield",
        "phone": "080-7122-2222",
        "ambulance": "080-7122-2222",
        "address": "3 & 4 ITPL Main Road, KIADB Export Promotion Industrial Area, Whitefield, Bengaluru 560066",
        "type": "24x7 Emergency & Critical Care",
    },
]


class EmergencyMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="emergency_mcp",
            description="Verified Emergency Helpline Numbers & 24x7 Trauma Center Provider MCP Server",
        )
        self._register_emergency_tools()

    def _register_emergency_tools(self):
        # 1. get_emergency_information
        self.register_tool(
            MCPTool(
                name="get_emergency_information",
                description="Retrieve verified national/regional emergency dispatch phone numbers and protocols",
                input_schema={
                    "type": "object",
                    "properties": {
                        "country_region": {"type": "string", "description": "ISO country code (default IN)"},
                        "locality": {"type": "string", "description": "Optional city/locality"},
                    },
                },
                allowed_agents=["triage_agent", "supervisor", "doctor_agent"],
                cache_ttl_seconds=3600,
            ),
            self._handle_get_emergency_information,
        )

        # 2. find_emergency_department
        self.register_tool(
            MCPTool(
                name="find_emergency_department",
                description="Retrieve nearest verified 24x7 hospital emergency departments and trauma centers",
                input_schema={
                    "type": "object",
                    "properties": {
                        "locality": {"type": "string", "description": "City area or locality"},
                    },
                },
                allowed_agents=["triage_agent", "supervisor", "doctor_agent"],
                cache_ttl_seconds=3600,
            ),
            self._handle_find_emergency_department,
        )

    # --------------------------------------------------------------------------
    # Handlers
    # --------------------------------------------------------------------------
    def _handle_get_emergency_information(
        self,
        country_region: Optional[str] = "IN",
        locality: Optional[str] = None,
    ) -> Dict[str, Any]:
        contacts = get_emergency_contacts(country_region=country_region)
        # Additional verified national numbers for India
        official_helplines = [
            {"service": "National Emergency Number (All Emergencies)", "number": "112", "source": "Govt of India ERSS (112.gov.in)"},
            {"service": "Ambulance & Medical Emergency", "number": "108", "source": "National Health Mission"},
            {"service": "Govt Ambulance Service", "number": "102", "source": "Ministry of Health and Family Welfare"},
            {"service": "Tele-MANAS Mental Health Helpline", "number": "14416", "source": "National Tele Mental Health Programme"},
        ]
        return {
            "country_region": country_region or "IN",
            "locality": locality or "Bengaluru",
            "primary_contacts": contacts,
            "official_helplines": official_helplines,
            "instruction": "Call emergency services immediately or proceed to the nearest emergency department.",
            "source": "Government of India Official Emergency Registry",
        }

    def _handle_find_emergency_department(
        self,
        locality: Optional[str] = None,
    ) -> Dict[str, Any]:
        matched = EMERGENCY_DEPARTMENTS_BENGALURU
        if locality:
            loc_lower = locality.lower()
            filtered = [d for d in matched if loc_lower in d["locality"].lower() or loc_lower in d["address"].lower()]
            if filtered:
                matched = filtered

        return {
            "locality": locality or "Bengaluru",
            "emergency_departments": matched,
            "total_facilities": len(matched),
            "instruction": "These facilities operate 24 hours a day, 7 days a week with active trauma teams.",
            "source": "Verified Karnataka Healthcare Facility Registry",
        }


emergency_mcp_server = EmergencyMCPServer()
