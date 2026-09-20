from fastapi import APIRouter
from app.models.dashboard import (
    DashboardState,
    PatientInfo,
    Symptom,
    SuggestedDepartment,
    Doctor,
    TimeSlot,
    AppointmentSummary,
)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardState)
async def get_dashboard_state() -> DashboardState:
    """Return initial mock healthcare dashboard state."""
    return DashboardState(
        patient=PatientInfo(
            name="Sarah Connor",
            age=32,
            phone="+1 (555) 019-2834",
        ),
        symptoms=[
            Symptom(name="Fever", duration="2 days"),
            Symptom(name="Headache", duration="1 day"),
            Symptom(name="Fatigue", duration="3 days"),
        ],
        suggestedDepartment=SuggestedDepartment(
            name="General Medicine",
        ),
        doctors=[
            Doctor(
                id="d1",
                name="Dr. Alex Taylor",
                department="General Medicine",
                availableStatus="Available",
            ),
            Doctor(
                id="d2",
                name="Dr. Brenda Vance",
                department="Internal Medicine",
                availableStatus="Available",
            ),
            Doctor(
                id="d3",
                name="Dr. Marcus Reed",
                department="Neurology",
                availableStatus="Unavailable",
            ),
        ],
        availableSlots=[
            TimeSlot(id="s1", date="Tomorrow, Oct 24", time="09:30 AM", doctor="Dr. Alex Taylor", isAvailable=True),
            TimeSlot(id="s2", date="Tomorrow, Oct 24", time="11:00 AM", doctor="Dr. Alex Taylor", isAvailable=True),
            TimeSlot(id="s3", date="Tomorrow, Oct 24", time="02:15 PM", doctor="Dr. Brenda Vance", isAvailable=True),
            TimeSlot(id="s4", date="Tomorrow, Oct 24", time="04:00 PM", doctor="Dr. Brenda Vance", isAvailable=False),
        ],
        appointmentSummary=AppointmentSummary(
            doctor="Dr. Alex Taylor",
            department="General Medicine",
            date="Tomorrow, Oct 24",
            time="11:00 AM",
            status="Pending Confirmation",
        ),
    )
