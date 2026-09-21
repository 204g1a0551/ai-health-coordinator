"""
Appointment MCP Server
Controlled operations for slot discovery, holding, booking, rescheduling, and cancellation.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.services.provider_service import provider_service
from app.services.redis_service import redis_service
from app.db.repository import (
    revalidate_slot,
    book_appointment as repo_book_appointment,
    cancel_appointment as repo_cancel_appointment,
    get_active_appointment as repo_get_active_appointment,
    find_doctor_by_name,
)


class AppointmentMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="appointment_mcp",
            description="Controlled Healthcare Appointment and Slot Management MCP Server",
        )
        self._register_appointment_tools()

    def _register_appointment_tools(self):
        # 1. get_available_slots
        self.register_tool(
            MCPTool(
                name="get_available_slots",
                description="Retrieve real-time verified consultation slots for a specific doctor",
                input_schema={
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "string", "description": "Doctor unique identifier"},
                        "date": {"type": "string", "description": "Date requested (e.g. tomorrow, 2026-09-22)"},
                        "period": {"type": "string", "description": "Optional period: morning, afternoon, evening"},
                    },
                    "required": ["doctor_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
                cache_ttl_seconds=60,
            ),
            self._handle_get_available_slots,
        )

        # 2. hold_slot
        self.register_tool(
            MCPTool(
                name="hold_slot",
                description="Acquire a temporary reservation hold on an appointment slot in Redis (e.g. 10 min TTL)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "string", "description": "Doctor unique identifier"},
                        "date": {"type": "string", "description": "Appointment date"},
                        "time": {"type": "string", "description": "Slot time (e.g. 6:00 PM)"},
                        "session_id": {"type": "string", "description": "Client session holding the slot"},
                    },
                    "required": ["doctor_id", "date", "time", "session_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
            ),
            self._handle_hold_slot,
        )

        # 3. book_appointment
        self.register_tool(
            MCPTool(
                name="book_appointment",
                description="Validate, recheck availability, and confirm booking in PostgreSQL with dual-persistence",
                input_schema={
                    "type": "object",
                    "properties": {
                        "doctor_id": {"type": "string", "description": "Doctor identifier or doctor name"},
                        "time": {"type": "string", "description": "Slot time (e.g. 6:00 PM)"},
                        "date": {"type": "string", "description": "Appointment date (e.g. tomorrow)"},
                        "session_id": {"type": "string", "description": "Session tracking the booking"},
                        "patient_name": {"type": "string", "description": "Optional patient display name"},
                    },
                    "required": ["doctor_id", "time", "session_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
            ),
            self._handle_book_appointment,
        )

        # 4. cancel_appointment
        self.register_tool(
            MCPTool(
                name="cancel_appointment",
                description="Cancel an active appointment and restore slot availability in database",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session identifier of the booking"},
                    },
                    "required": ["session_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
            ),
            self._handle_cancel_appointment,
        )

        # 5. reschedule_appointment
        self.register_tool(
            MCPTool(
                name="reschedule_appointment",
                description="Reschedule an active appointment to a newly revalidated date and time",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session identifier"},
                        "doctor_id": {"type": "string", "description": "Doctor identifier or name"},
                        "new_time": {"type": "string", "description": "New slot time (e.g. 10:00 AM)"},
                        "new_date": {"type": "string", "description": "New appointment date"},
                    },
                    "required": ["session_id", "doctor_id", "new_time"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
            ),
            self._handle_reschedule_appointment,
        )

        # 6. get_appointment
        self.register_tool(
            MCPTool(
                name="get_appointment",
                description="Retrieve currently booked active appointment details for a session or user",
                input_schema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string", "description": "Session identifier"},
                    },
                    "required": ["session_id"],
                },
                allowed_agents=["doctor_agent", "supervisor", "doctor_slot_agent"],
            ),
            self._handle_get_appointment,
        )

    # --------------------------------------------------------------------------
    # Handlers
    # --------------------------------------------------------------------------
    def _handle_get_available_slots(
        self,
        doctor_id: str,
        date: Optional[str] = None,
        period: Optional[str] = None,
    ) -> Dict[str, Any]:
        slots = provider_service.get_available_slots(doctor_id=doctor_id, date=date, period=period)
        return {
            "doctor_id": doctor_id,
            "date": date or "tomorrow",
            "slots": slots,
            "total_slots": len(slots),
            "source": provider_service.provider.provider_name,
        }

    def _handle_hold_slot(
        self,
        doctor_id: str,
        date: str,
        time: str,
        session_id: str,
    ) -> Dict[str, Any]:
        # Lock in Redis for 10 minutes (600 seconds)
        acquired = redis_service.acquire_slot_lock(
            doctor_id=doctor_id,
            date=date,
            time=time,
            session_id=session_id,
            ttl_seconds=600,
        )
        return {
            "doctor_id": doctor_id,
            "date": date,
            "time": time,
            "hold_acquired": acquired,
            "ttl_seconds": 600 if acquired else 0,
            "message": "Slot held for 10 minutes" if acquired else "Slot is already reserved by another user",
        }

    def _handle_book_appointment(
        self,
        doctor_id: str,
        time: str,
        session_id: str,
        date: Optional[str] = "tomorrow",
        patient_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Perform controlled repository booking
        result = repo_book_appointment(
            session_id=session_id,
            doctor_query=doctor_id,
            time_query=time,
            date_query=date,
        )
        # Invalidate Redis availability cache for this doctor
        redis_service.invalidate_slot_cache(doctor_id, date or "tomorrow")
        return result

    def _handle_cancel_appointment(self, session_id: str) -> Dict[str, Any]:
        result = repo_cancel_appointment(session_id=session_id)
        return result

    def _handle_reschedule_appointment(
        self,
        session_id: str,
        doctor_id: str,
        new_time: str,
        new_date: Optional[str] = "tomorrow",
    ) -> Dict[str, Any]:
        # Cancel current appointment first
        cancel_res = repo_cancel_appointment(session_id=session_id)
        if not cancel_res.get("success", False) and "No active" not in cancel_res.get("error", ""):
            return cancel_res

        # Book new slot
        book_res = repo_book_appointment(
            session_id=session_id,
            doctor_query=doctor_id,
            time_query=new_time,
            date_query=new_date,
        )
        return {
            "rescheduled": book_res.get("success", False),
            "new_appointment": book_res.get("appointment"),
            "error": book_res.get("error"),
        }

    def _handle_get_appointment(self, session_id: str) -> Dict[str, Any]:
        appt = repo_get_active_appointment(session_id=session_id)
        if not appt:
            return {"found": False, "appointment": None, "message": "No active appointment found"}
        return {"found": True, "appointment": appt}


appointment_mcp_server = AppointmentMCPServer()
