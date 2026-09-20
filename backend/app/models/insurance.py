from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PolicyUploadCategory(str, Enum):
    COMPANY_HEALTH_INSURANCE = "COMPANY_HEALTH_INSURANCE"
    EMPLOYEE_REIMBURSEMENT = "EMPLOYEE_REIMBURSEMENT"
    INSURANCE_TERMS_CONDITIONS = "INSURANCE_TERMS_CONDITIONS"
    PHARMACY_REIMBURSEMENT = "PHARMACY_REIMBURSEMENT"


class CoverageCategoryItem(BaseModel):
    category: str = Field(description="Name of coverage category e.g. Inpatient Hospitalization, Outpatient (OPD), Pharmacy")
    status: str = Field(description="Covered, Excluded, or Conditional")
    details: str = Field(description="Specific terms and sub-limits mentioned in policy")


class PolicyExclusionItem(BaseModel):
    category: str = Field(description="Exclusion category e.g. Cosmetic, Pre-existing waiting period, Experimental")
    clause_reference: Optional[str] = Field(default=None, description="Clause title or page")
    description: str = Field(description="Exclusion details as stated in the policy")


class ReimbursementLimit(BaseModel):
    scope: str = Field(description="e.g. Annual Sum Insured, OPD Limit, Medicine Cap, Room Rent")
    amount: str = Field(description="e.g. ₹5,00,000 / ₹5,000 per year / 1% of sum insured")
    notes: Optional[str] = Field(default=None, description="Co-pay or deductible requirements")


class PharmacyRule(BaseModel):
    rule: str = Field(description="Rule regarding prescription medicines or pharmacies")
    prescription_required: bool = Field(default=True, description="Whether doctor prescription is mandatory")
    approved_network_only: bool = Field(default=False, description="Whether only network pharmacies are reimbursable")
    details: str = Field(description="Explanation of pharmacy policy requirements")


class OutpatientInpatientRule(BaseModel):
    setting: str = Field(description="Outpatient (OPD) or Inpatient (IPD)")
    minimum_hospitalization_hours: Optional[str] = Field(default=None, description="e.g. 24 hours for IPD or Day Care list")
    eligibility_summary: str = Field(description="Eligibility rules for this care setting")


class RequiredDocument(BaseModel):
    document_name: str = Field(description="e.g. Original Tax Invoice, Prescribing Doctor's Note, Discharge Summary")
    mandatory: bool = Field(default=True, description="Whether document is strictly required")
    purpose: str = Field(description="Reason document is required by claims administrator")


class ClaimSubmissionDeadline(BaseModel):
    timeframe: str = Field(description="e.g. 30 days from date of purchase / 15 days from discharge")
    penalty_or_forfeiture: Optional[str] = Field(default=None, description="Terms on late submissions")


class ExtractedPolicyRules(BaseModel):
    policy_id: str
    policy_name: str
    policy_category: PolicyUploadCategory
    coverage_categories: List[CoverageCategoryItem] = []
    exclusions: List[PolicyExclusionItem] = []
    reimbursement_limits: List[ReimbursementLimit] = []
    pharmacy_medicine_rules: List[PharmacyRule] = []
    outpatient_inpatient_rules: List[OutpatientInpatientRule] = []
    required_documents: List[RequiredDocument] = []
    claim_submission_deadlines: List[ClaimSubmissionDeadline] = []
    summary: str
    extracted_at: str


class EvidenceItem(BaseModel):
    policy_name: str
    page_number: int
    clause_title: Optional[str] = None
    quote: str


class CoverageAssessmentStatus(str, Enum):
    POTENTIALLY_COVERED = "Potentially covered"
    LIKELY_EXCLUDED = "Likely excluded"
    CONDITIONALLY_ELIGIBLE = "Conditionally eligible"
    INSUFFICIENT_INFORMATION = "Insufficient information to determine eligibility"


class CoverageComparisonRequest(BaseModel):
    policy_id: str
    medical_document_id: Optional[str] = None
    user_query: Optional[str] = None  # e.g. "Will this medicine bill be covered according to my company policy?"


class CoverageComparisonResponse(BaseModel):
    coverage_assessment: str = Field(
        description="e.g. 'Potentially covered', 'Likely excluded', 'Conditionally eligible'"
    )
    reason: str = Field(
        description="Grounding explanation using compliant language like 'The uploaded policy states...'"
    )
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Direct citations with page numbers")
    conditions: List[str] = Field(
        default_factory=list,
        description="Mandatory criteria (e.g. Required prescription, Original invoice, Applicable reimbursement limit)"
    )
    confidence: str = Field(
        description="'Policy information appears sufficient' or 'Policy information appears insufficient'"
    )
    applicable_limit: Optional[str] = Field(default=None, description="Relevant monetary or frequency limit")
    required_documents: List[str] = Field(default_factory=list, description="Documents required to submit claim")
    deadline: Optional[str] = Field(default=None, description="Claim submission deadline")
    disclaimer: str = Field(
        default=(
            "Important: Never assume that an insurance company or employer will definitely approve or reject a claim. "
            "This analysis reflects the clauses of the uploaded policy document. "
            "The final claim adjudication belongs exclusively to the insurer, employer, or third-party administrator (TPA)."
        ),
        description="Regulatory non-adjudication safety notice"
    )


class PolicyQuestionRequest(BaseModel):
    policy_id: Optional[str] = None
    question: str


class PolicyAnswerResponse(BaseModel):
    answer: str
    evidence: List[EvidenceItem] = []
    confidence: str
    disclaimer: str
