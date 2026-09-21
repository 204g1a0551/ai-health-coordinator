from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    DOCTOR_CONSULTATION = "DOCTOR_CONSULTATION"
    MEDICAL_REPORT = "MEDICAL_REPORT"
    MEDICINE_BILL = "MEDICINE_BILL"
    INSURANCE_POLICY = "INSURANCE_POLICY"
    REIMBURSEMENT_POLICY = "REIMBURSEMENT_POLICY"
    OTHER = "OTHER"


class ExtractedMedicine(BaseModel):
    name: str = Field(description="Name of the medicine explicitly written in document")
    dosage: Optional[str] = Field(default=None, description="Dosage e.g. 500mg, 10ml, as written")
    frequency: Optional[str] = Field(default=None, description="Frequency e.g. 1-0-1, Once daily, TDS, as written")
    duration: Optional[str] = Field(default=None, description="Duration of medication if specified e.g. 5 days")
    instructions: Optional[str] = Field(default=None, description="Instructions e.g. After meals, with water")


class DoctorHospitalInfo(BaseModel):
    doctor_name: Optional[str] = Field(default=None, description="Name of consulting doctor if present")
    hospital_name: Optional[str] = Field(default=None, description="Hospital or clinic name")
    department: Optional[str] = Field(default=None, description="Medical department or specialty")
    qualifications: Optional[str] = Field(default=None, description="Doctor degrees e.g. MBBS, MD")
    registration_no: Optional[str] = Field(default=None, description="Doctor medical council registration number")
    contact: Optional[str] = Field(default=None, description="Hospital/clinic contact number or address")


class DocumentDates(BaseModel):
    document_date: Optional[str] = Field(default=None, description="Date on which document was generated/signed")
    consultation_date: Optional[str] = Field(default=None, description="Date of clinical consultation")
    valid_until: Optional[str] = Field(default=None, description="Expiry date or next follow up date")
    admission_date: Optional[str] = Field(default=None, description="Hospital admission date if applicable")
    discharge_date: Optional[str] = Field(default=None, description="Hospital discharge date if applicable")


class PolicyClause(BaseModel):
    title: str = Field(description="Clause or benefit title e.g. Cashless Hospitalization, OPD Reimbursement")
    description: str = Field(description="Clause description extracted verbatim or summarized from text")
    category: Optional[str] = Field(default=None, description="Category: e.g. Benefit, Exclusion, Co-Pay, Waiting Period")


class PolicyReimbursementInfo(BaseModel):
    coverage_amount: Optional[str] = Field(default=None, description="Total sum insured or coverage limit e.g. ₹5,00,000")
    claim_limit: Optional[str] = Field(default=None, description="Per-incident or annual sub-limit")
    eligible_expenses: List[str] = Field(default_factory=list, description="Explicitly covered medical expenses")
    ineligible_expenses: List[str] = Field(default_factory=list, description="Non-covered or excluded expenses")
    clauses: List[PolicyClause] = Field(default_factory=list, description="Extracted policy or reimbursement clauses")
    co_pay_percentage: Optional[str] = Field(default=None, description="Co-pay required if stated")
    claim_submission_deadline: Optional[str] = Field(default=None, description="Deadline for claim submission e.g. 30 days")


class ExtractedDocumentData(BaseModel):
    document_type: DocumentType = Field(description="Identified document category")
    confidence_score: float = Field(default=0.95, description="Classification confidence (0.0 to 1.0)")
    patient_name: Optional[str] = Field(default=None, description="Patient name if explicitly mentioned")
    medicines: List[ExtractedMedicine] = Field(default_factory=list, description="Medicines explicitly written in document")
    doctor_hospital: Optional[DoctorHospitalInfo] = Field(default=None, description="Doctor and hospital details")
    dates: Optional[DocumentDates] = Field(default=None, description="Important document dates")
    policy_reimbursement: Optional[PolicyReimbursementInfo] = Field(default=None, description="Insurance or reimbursement clauses")
    diagnosis_findings: List[str] = Field(default_factory=list, description="Diagnoses, symptoms or lab findings explicitly stated")
    total_amount: Optional[str] = Field(default=None, description="Total amount billed or paid if applicable")
    clinical_notes_summary: Optional[str] = Field(default=None, description="Concise summary of clinical/policy notes")
    raw_text_snippet: Optional[str] = Field(default=None, description="Representative excerpt of extracted text")
    disclaimer: str = Field(
        default="Important Notice: The information presented here is extracted directly from the uploaded document for clinical coordination and tracking purposes. It does NOT constitute independent medical advice or a clinical diagnosis.",
        description="Clinical safety notice"
    )


class ProcessingStage(BaseModel):
    stage: str
    message: str
    status: str = "completed"  # pending, in_progress, completed, failed
    timestamp: str


class DocumentUploadResponse(BaseModel):
    id: str
    file_name: str
    file_size: int
    processing_status: str
    stages: List[ProcessingStage] = []
    extracted_data: Optional[ExtractedDocumentData] = None
    created_at: str
    error_message: Optional[str] = None


class DocumentListItem(BaseModel):
    id: str
    file_name: str
    file_size: int
    document_type: str
    doctor_or_hospital: Optional[str] = None
    document_date: Optional[str] = None
    medicines_count: int = 0
    processing_status: str
    created_at: str
