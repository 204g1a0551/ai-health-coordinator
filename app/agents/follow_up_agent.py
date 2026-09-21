"""
Proactive Follow-Up Agent.
Autonomous agent responsible for patient post-consultation and medication recovery check-ins.
Decoupled from the synchronous LangGraph coordinator.
"""

import logging
from typing import Dict, Any, List, Optional
from app.models.follow_up import (
    FollowUpTask,
    FollowUpCreateRequest,
    FollowUpResponseRequest,
)
from app.services.follow_up_service import follow_up_service
from app.agents.state import AgentState

logger = logging.getLogger("follow_up_agent")


class ProactiveFollowUpAgent:
    """
    Sub-agent: Proactive Follow-Up Agent
    Responsibilities:
    1. Manage the asynchronous post-appointment and post-prescription recovery check-in lifecycle.
    2. Coordinate multi-channel notification dispatches (WhatsApp, SMS, App Notification).
    3. Evaluate patient recovery responses (categorizing into RECOVERED, BETTER, STABLE, or ESCALATE_TO_TRIAGE).
    4. Provide localized follow-up in the patient's native tongue (Telugu, Hindi, English).
    """

    def __init__(self):
        self.service = follow_up_service

    def schedule_appointment_followup(
        self,
        patient_id: str,
        patient_name: str,
        doctor: str,
        department: str,
        appointment_id: str,
        patient_language: str = "en",
        patient_phone: Optional[str] = None
    ) -> FollowUpTask:
        """Schedules a +48 hour recovery check-in following an appointment."""
        return self.service.schedule_follow_up(FollowUpCreateRequest(
            patient_id=patient_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            patient_language=patient_language,
            source_type="APPOINTMENT",
            source_id=appointment_id,
            delay_hours=48.0,
            clinical_context={
                "doctor": doctor,
                "department": department,
                "appointment_id": appointment_id,
            }
        ))

    def schedule_prescription_followup(
        self,
        patient_id: str,
        patient_name: str,
        document_id: str,
        medicines: List[str],
        patient_language: str = "en",
        patient_phone: Optional[str] = None
    ) -> FollowUpTask:
        """Schedules a +48 hour medication tolerance & adherence check-in."""
        return self.service.schedule_follow_up(FollowUpCreateRequest(
            patient_id=patient_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            patient_language=patient_language,
            source_type="PRESCRIPTION",
            source_id=document_id,
            delay_hours=48.0,
            clinical_context={
                "document_id": document_id,
                "medicines": medicines,
            }
        ))

    def trigger_simulation(self, task_id: str) -> Optional[FollowUpTask]:
        """Simulates immediate Day 2 trigger for testing and demonstration."""
        return self.service.trigger_task_now(task_id)

    def process_patient_reply(self, task_id: str, reply_text: str) -> Optional[FollowUpTask]:
        """Processes patient response to follow-up check."""
        return self.service.record_patient_response(FollowUpResponseRequest(
            task_id=task_id,
            response_text=reply_text
        ))


follow_up_agent = ProactiveFollowUpAgent()
