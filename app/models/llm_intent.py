from typing import List, Optional
from pydantic import BaseModel, Field


class ExtractedSymptom(BaseModel):
    name: str = Field(..., description="Symptom name (e.g. Headache, Fever)")
    duration: Optional[str] = Field(default=None, description="Reported duration (e.g. 2 days)")


class ParsedUserIntent(BaseModel):
    """
    Structured natural language output extracted by the LLM layer.
    Strictly decoupled from database and storage execution.
    """
    intent: str = Field(
        ...,
        description=(
            "Primary intent: 'EXTRACT_SYMPTOMS', 'SEARCH_DOCTOR', 'FILTER_SLOTS', "
            "'SEARCH_NEARBY', 'BOOK_APPOINTMENT', 'CANCEL_APPOINTMENT', "
            "'UPDATE_PATIENT', 'CLARIFICATION', or 'GENERAL'"
        ),
    )
    symptoms: List[ExtractedSymptom] = Field(
        default_factory=list,
        description="List of detected symptoms and durations",
    )
    department: Optional[str] = Field(
        default=None,
        description="Identified medical department (e.g. General Medicine, ENT, Dermatology)",
    )
    location: Optional[str] = Field(
        default=None,
        description="Target locality in Bengaluru (e.g. Indiranagar, Koramangala, Whitefield)",
    )
    date: Optional[str] = Field(
        default=None,
        description="Preferred appointment date or relative day (e.g. tomorrow, Saturday, 2026-09-21)",
    )
    time: Optional[str] = Field(
        default=None,
        description="Preferred time or period of day (e.g. 6:00 PM, evening, morning)",
    )
    doctor: Optional[str] = Field(
        default=None,
        description="Target doctor name (e.g. Dr. Ravi Kumar, Dr. Priya Sharma)",
    )
    appointment_action: Optional[str] = Field(
        default=None,
        description="Appointment action type ('BOOK', 'CANCEL', 'RESCHEDULE', 'STATUS', 'CLEAR')",
    )
    selected_option_index: Optional[int] = Field(
        default=None,
        description="Ordinal reference for selection (1 for first option, 2 for second option, etc.)",
    )
    is_change_or_correction: bool = Field(
        default=False,
        description="True if the message modifies previous criteria (e.g. 'Actually, change that to Saturday')",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if required information is missing to proceed safely",
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Clarification question to ask the user when required details are missing",
    )
