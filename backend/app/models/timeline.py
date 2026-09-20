from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TimelineEventType(str, Enum):
    CONSULTATION = "CONSULTATION"
    PRESCRIPTION = "PRESCRIPTION"
    LAB_REPORT = "LAB_REPORT"
    PHARMACY_BILL = "PHARMACY_BILL"
    FOLLOW_UP = "FOLLOW_UP"
    INSURANCE = "INSURANCE"


class TimelineEvent(BaseModel):
    event_id: str
    session_id: str
    event_type: TimelineEventType
    date: Optional[str] = None
    doctor: Optional[str] = None
    hospital: Optional[str] = None
    medicines: List[str] = Field(default_factory=list)
    bill_amount: Optional[float] = None
    consultation_amount: Optional[float] = None
    diagnostic_amount: Optional[float] = None
    doc_id: str
    doc_type: str
    summary: str = ""
    created_at: str


class MedicalExpense(BaseModel):
    expense_id: str
    session_id: str
    category: str
    amount: float
    date: Optional[str] = None
    provider: Optional[str] = None
    doc_id: str


class ExpenseSummary(BaseModel):
    monthly_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    category_totals: Dict[str, float] = Field(default_factory=dict)
    total: float = 0.0
    expenses: List[MedicalExpense] = Field(default_factory=list)


class TimelineQueryResponse(BaseModel):
    events: List[TimelineEvent] = Field(default_factory=list)
    summary: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)

