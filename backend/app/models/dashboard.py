from typing import List, Optional
from pydantic import BaseModel, Field


class PatientInfo(BaseModel):
    name: str = Field(default="", description="Patient Name")
    age: Optional[int] = Field(default=None, description="Age")
    phone: Optional[str] = Field(default="", description="Phone")


class Symptom(BaseModel):
    name: str
    duration: Optional[str] = None


class SuggestedDepartment(BaseModel):
    name: str = Field(default="", description="Department name")


class Doctor(BaseModel):
    id: str
    name: str
    department: str
    available_status: str = Field(default="Available", alias="availableStatus")

    class Config:
        populate_by_name = True


class TimeSlot(BaseModel):
    id: str
    date: str
    time: str
    doctor: str
    is_available: bool = Field(default=True, alias="isAvailable")

    class Config:
        populate_by_name = True


class AppointmentSummary(BaseModel):
    doctor: str = ""
    department: str = ""
    date: str = ""
    time: str = ""
    status: str = "Pending"


class DashboardState(BaseModel):
    patient: PatientInfo
    symptoms: List[Symptom] = Field(default_factory=list)
    suggested_department: SuggestedDepartment = Field(default_factory=SuggestedDepartment, alias="suggestedDepartment")
    doctors: List[Doctor] = Field(default_factory=list)
    available_slots: List[TimeSlot] = Field(default_factory=list, alias="availableSlots")
    appointment_summary: AppointmentSummary = Field(default_factory=AppointmentSummary, alias="appointmentSummary")

    class Config:
        populate_by_name = True
