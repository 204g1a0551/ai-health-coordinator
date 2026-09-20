from typing import List, Optional
from pydantic import BaseModel, Field


class Patient(BaseModel):
    name: str = Field(default="John Doe", description="Full name of the patient")
    age: Optional[int] = Field(default=34, description="Age of the patient")
    gender: Optional[str] = Field(default="Male", description="Gender of the patient")
    contact: Optional[str] = Field(default="+1 (555) 234-5678", description="Contact phone or email")


class SymptomItem(BaseModel):
    name: str
    severity: str = Field(default="Moderate", description="Mild, Moderate, Severe")
    duration: Optional[str] = Field(default="2 days", description="Duration of the symptom")


class Department(BaseModel):
    name: str = Field(default="General Medicine", description="Suggested medical department")
    confidence: Optional[str] = Field(default="High", description="Recommendation confidence")
    description: Optional[str] = Field(
        default="Primary care diagnosis and treatment for acute symptoms.",
        description="Brief overview of department specialty"
    )


class Doctor(BaseModel):
    id: str
    name: str
    specialty: str
    qualification: str
    experience: str


class TimeSlot(BaseModel):
    id: str
    doctor_id: str
    time: str
    date: str
    is_available: bool = True


class AppointmentSummary(BaseModel):
    patient_name: str = "John Doe"
    department: str = "General Medicine"
    doctor_name: str = "Dr. Sarah Jenkins, MD"
    slot_time: str = "10:30 AM"
    appointment_date: str = "Tomorrow, Oct 24"
    status: str = "Pending Confirmation"


class DashboardState(BaseModel):
    patient: Patient
    symptoms: List[SymptomItem]
    suggested_department: Department
    available_doctors: List[Doctor]
    available_time_slots: List[TimeSlot]
    appointment_summary: AppointmentSummary
