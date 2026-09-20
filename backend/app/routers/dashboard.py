from fastapi import APIRouter
from app.models.dashboard import (
    DashboardState,
    Patient,
    SymptomItem,
    Department,
    Doctor,
    TimeSlot,
    AppointmentSummary,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardState)
async def get_dashboard_state() -> DashboardState:
    """Return the initial healthcare dashboard state."""
    return DashboardState(
        patient=Patient(
            name="John Doe",
            age=34,
            gender="Male",
            contact="+1 (555) 234-5678",
        ),
        symptoms=[
            SymptomItem(name="Persistent Dry Cough", severity="Moderate", duration="3 days"),
            SymptomItem(name="Mild Fever (100.2°F)", severity="Mild", duration="2 days"),
            SymptomItem(name="Fatigue & Body Aches", severity="Mild", duration="1 day"),
        ],
        suggested_department=Department(
            name="General Medicine",
            confidence="High",
            description="Recommended for initial evaluation of respiratory and febrile symptoms.",
        ),
        available_doctors=[
            Doctor(
                id="doc-1",
                name="Dr. Sarah Jenkins, MD",
                specialty="General Internal Medicine",
                qualification="MD, Harvard Medical School",
                experience="12 years",
            ),
            Doctor(
                id="doc-2",
                name="Dr. Robert Miller, MD",
                specialty="Pulmonology & Respiratory Care",
                qualification="MD, Johns Hopkins",
                experience="15 years",
            ),
            Doctor(
                id="doc-3",
                name="Dr. Emily Chen, DO",
                specialty="Family & Community Medicine",
                qualification="DO, Stanford Medicine",
                experience="8 years",
            ),
        ],
        available_time_slots=[
            TimeSlot(id="slot-1", doctor_id="doc-1", time="09:30 AM", date="Tomorrow, Oct 24", is_available=True),
            TimeSlot(id="slot-2", doctor_id="doc-1", time="10:30 AM", date="Tomorrow, Oct 24", is_available=True),
            TimeSlot(id="slot-3", doctor_id="doc-1", time="02:00 PM", date="Tomorrow, Oct 24", is_available=True),
            TimeSlot(id="slot-4", doctor_id="doc-2", time="11:15 AM", date="Tomorrow, Oct 24", is_available=True),
            TimeSlot(id="slot-5", doctor_id="doc-2", time="03:30 PM", date="Tomorrow, Oct 24", is_available=False),
            TimeSlot(id="slot-6", doctor_id="doc-3", time="04:00 PM", date="Tomorrow, Oct 24", is_available=True),
        ],
        appointment_summary=AppointmentSummary(
            patient_name="John Doe",
            department="General Medicine",
            doctor_name="Dr. Sarah Jenkins, MD",
            slot_time="10:30 AM",
            appointment_date="Tomorrow, Oct 24",
            status="Pending Confirmation",
        ),
    )
