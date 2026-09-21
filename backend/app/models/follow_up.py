"""
Pydantic Models for Proactive Follow-Up Agent.
Manages asynchronous 48-hour scheduled follow-up tasks and multi-channel notifications.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class FollowUpStatus(str, Enum):
    PENDING = "PENDING"
    DUE = "DUE"
    DISPATCHED = "DISPATCHED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class NotificationChannel(str, Enum):
    APP_NOTIFICATION = "APP_NOTIFICATION"
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"


class FollowUpNotification(BaseModel):
    notification_id: str
    channel: str
    recipient: str
    message: str
    language: str = "en"
    dispatched_at: str
    status: str = "DELIVERED"
    delivery_metadata: Optional[Dict[str, Any]] = None


class FollowUpTask(BaseModel):
    task_id: str = Field(..., description="Unique follow-up task ID (e.g. FLW-82931)")
    patient_id: str = Field(..., description="Patient identifier or session ID")
    patient_name: str = Field("Patient", description="Patient name")
    patient_phone: Optional[str] = Field(None, description="Patient contact phone number")
    patient_language: str = Field("en", description="Preferred language (te, hi, en, etc.)")
    source_type: str = Field("APPOINTMENT", description="Source: APPOINTMENT or PRESCRIPTION")
    source_id: str = Field(..., description="Appointment ID or Document ID")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    trigger_at: str = Field(..., description="Scheduled execution timestamp (+48 hours)")
    status: FollowUpStatus = Field(FollowUpStatus.PENDING, description="Current task state")
    channels: List[str] = Field(
        default_factory=lambda: ["APP_NOTIFICATION", "SMS", "WHATSAPP"],
        description="Target dispatch channels"
    )
    clinical_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Clinical context (doctor, department, medicines, symptoms)"
    )
    follow_up_prompt_english: Optional[str] = None
    follow_up_prompt_vernacular: Optional[str] = None
    notifications: List[FollowUpNotification] = Field(default_factory=list)
    patient_response: Optional[Dict[str, Any]] = None


class FollowUpCreateRequest(BaseModel):
    patient_id: str
    patient_name: Optional[str] = "Patient"
    patient_phone: Optional[str] = None
    patient_language: Optional[str] = "en"
    source_type: str = "APPOINTMENT"
    source_id: str
    delay_hours: float = Field(48.0, description="Hours until follow-up (default: 48)")
    clinical_context: Optional[Dict[str, Any]] = None


class FollowUpResponseRequest(BaseModel):
    task_id: str
    response_text: str = Field(..., description="Patient response text (e.g. 'Feeling much better', 'Still having fever')")
    recovery_status: Optional[str] = Field("BETTER", description="BETTER, SAME, WORSE, or RECOVERED")
    language: Optional[str] = "en"
