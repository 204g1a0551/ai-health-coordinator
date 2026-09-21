from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class LabTestResult(BaseModel):
    test_name: str = Field(..., description="Name of laboratory test (e.g. Hemoglobin, Platelet Count, TSH)")
    result: str = Field(..., description="Observed numeric or qualitative test result (e.g. 13.4, 135,000, 5.42)")
    unit: str = Field(default="", description="Biological measurement unit (e.g. g/dL, /mcL, mg/dL, uIU/mL)")
    reference_range: str = Field(default="", description="Stated biological reference range from report (e.g. 12.0 - 15.0)")
    status: str = Field(default="NORMAL", description="Status: 'NORMAL', 'OUTSIDE_RANGE_HIGH', 'OUTSIDE_RANGE_LOW', 'OUTSIDE_RANGE'")
    is_out_of_range: bool = Field(default=False, description="True if value is outside explicitly stated reference range")
    source_page: int = Field(default=1, description="Page number where the test appears in the PDF report")
    panel_name: Optional[str] = Field(default=None, description="Panel name e.g. Complete Blood Count, Lipid Profile, Thyroid Profile")


class LabReportData(BaseModel):
    document_id: str
    file_name: str
    laboratory_name: str = Field(default="Metropolis Healthcare & Clinical Reference Lab")
    report_date: str = Field(default="2026-09-18")
    patient_name: Optional[str] = Field(default="Sarah Connor")
    page_count: int = Field(default=3)
    tests: List[LabTestResult] = Field(default_factory=list)
    total_tests: int = Field(default=0)
    out_of_range_count: int = Field(default=0)
    summary: str = Field(default="")
    disclaimer: str = Field(
        default=(
            "Important: Values marked as outside stated reference ranges are reported strictly as extracted "
            "from the laboratory document. This information is for clinical tracking only and does NOT constitute "
            "a medical diagnosis or clinical conclusion. Please consult a licensed physician."
        )
    )


class LabQuestionRequest(BaseModel):
    document_id: Optional[str] = None
    question: str


class LabQuestionResponse(BaseModel):
    question: str
    answer: str
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    source_page: Optional[int] = None
    referenced_tests: List[LabTestResult] = Field(default_factory=list)
    disclaimer: str


class LabEvidenceResponse(BaseModel):
    document_name: str
    page_number: int
    extracted_text: str
    explanation: str
    query: str
    relevant_tests: List[LabTestResult] = Field(default_factory=list)
    disclaimer: str
