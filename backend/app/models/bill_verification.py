from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class PrescriptionMedicineItem(BaseModel):
    name: str = Field(..., description="Prescribed medicine name (e.g. Paracetamol, Pantoprazole)")
    dosage: str = Field(default="", description="Dosage strength (e.g. 650mg, 40mg)")
    frequency: str = Field(default="", description="Frequency (e.g. 1-0-1, once daily)")
    duration: str = Field(default="", description="Duration (e.g. 5 days, 1 week)")
    calculated_quantity: int = Field(default=0, description="Calculated quantity based on frequency and duration")
    instructions: str = Field(default="", description="Instructions e.g. after food, before food")
    source_page: int = Field(default=1, description="Page in prescription PDF")


class BilledMedicineItem(BaseModel):
    name: str = Field(..., description="Medicine name as printed on pharmacy bill")
    dosage: str = Field(default="", description="Dosage if specified on bill")
    billed_quantity: int = Field(default=1, description="Quantity billed on invoice")
    unit_rate: float = Field(default=0.0, description="Unit price per tablet/strip")
    total_price: float = Field(default=0.0, description="Total line amount")
    source_page: int = Field(default=1, description="Page in bill document")


class MedicineComparisonItem(BaseModel):
    medicine_name: str
    prescription_spec: str = Field(..., description="Details from prescription (dosage, frequency, duration, qty)")
    bill_spec: str = Field(..., description="Details from bill (billed qty, rate, total)")
    difference_type: str = Field(
        ...,
        description="MATCH | MISSING_FROM_BILL | NOT_IN_PRESCRIPTION | QUANTITY_MISMATCH | DOSAGE_MISMATCH",
    )
    difference_description: str = Field(..., description="Plain-text explanation of difference")
    is_discrepancy: bool = Field(default=False)
    price_info: Optional[str] = Field(default=None)


class BillFinancialSummary(BaseModel):
    pharmacy_name: str = Field(default="Apollo Pharmacy, Bengaluru")
    gstin: str = Field(default="29AABCA1234F1Z5")
    invoice_no: str = Field(default="INV-98421")
    bill_date: str = Field(default="2026-09-20")
    subtotal: float = Field(default=120.0)
    gst_tax: float = Field(default=14.40)
    total_amount: float = Field(default=134.40)
    payment_mode: str = Field(default="UPI")


class BillVerificationData(BaseModel):
    prescription_id: str
    bill_id: str
    prescription_file: str
    bill_file: str
    patient_name: str = Field(default="Sarah Connor")
    doctor_name: str = Field(default="Dr. Ravi Kumar")
    clinic_name: str = Field(default="Apollo Clinic, Bangalore")
    financial_summary: BillFinancialSummary
    comparisons: List[MedicineComparisonItem] = Field(default_factory=list)
    total_prescribed: int = Field(default=0)
    total_billed: int = Field(default=0)
    matched_count: int = Field(default=0)
    discrepancy_count: int = Field(default=0)
    verification_status: str = Field(
        default="DISCREPANCIES_DETECTED",
        description="VERIFIED_MATCH | DISCREPANCIES_DETECTED",
    )
    disclaimer: str = Field(
        default=(
            "Important Safety Notice: This verification is strictly a factual textual comparison between the uploaded "
            "prescription and pharmacy bill. It does NOT determine whether a medicine is medically appropriate and does "
            "NOT recommend or endorse drug substitutions. Please consult your physician or licensed pharmacist."
        )
    )


class VerificationQuestionRequest(BaseModel):
    question: str
    prescription_id: Optional[str] = None
    bill_id: Optional[str] = None


class VerificationQuestionResponse(BaseModel):
    question: str
    answer: str
    referenced_items: List[MedicineComparisonItem] = Field(default_factory=list)
    source_documents: List[str] = Field(default_factory=list)
    disclaimer: str


class VerificationEvidenceData(BaseModel):
    prescription_text: str
    bill_text: str
    prescription_source: str
    bill_source: str
    detected_discrepancies: List[str] = Field(default_factory=list)
    disclaimer: str
