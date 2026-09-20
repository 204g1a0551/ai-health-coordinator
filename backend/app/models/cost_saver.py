from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class EquivalenceLevel(str, Enum):
    THERAPEUTIC_EQUIVALENT = "THERAPEUTIC_EQUIVALENT"
    PHARMACEUTICAL_EQUIVALENT = "PHARMACEUTICAL_EQUIVALENT"
    PHARMACEUTICAL_ALTERNATIVE = "PHARMACEUTICAL_ALTERNATIVE"
    UNVERIFIED = "UNVERIFIED"


class MedicinePriceItem(BaseModel):
    medicine_name: str = Field(description="Commercial brand or generic product name")
    active_ingredient: str = Field(description="Active pharmacological substance")
    strength: str = Field(description="Dose strength e.g. 650mg, 40mg, 625mg")
    dosage_form: str = Field(description="Dosage form e.g. Tablet, Capsule, Syrup")
    pack_size: str = Field(description="Packaging size e.g. Strip of 10 tablets")
    listed_price: float = Field(description="Current listed market or retail price in INR (₹)")
    price_per_unit: float = Field(description="Price per individual unit/tablet in INR (₹)")
    manufacturer: Optional[str] = Field(default=None, description="Manufacturer or marketing entity")
    is_generic: bool = Field(default=False, description="Whether this is a Jan Aushadhi / generic equivalent")
    source: str = Field(
        default="Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP) / NPPA National Reference",
        description="Authoritative pricing reference source"
    )
    price_timestamp: str = Field(default="2026-09-01T00:00:00Z", description="Price verification timestamp")


class MedicineComparison(BaseModel):
    prescribed_medicine: MedicinePriceItem = Field(description="Details of prescribed medicine")
    generic_equivalent: Optional[MedicinePriceItem] = Field(
        default=None,
        description="Identified verified generic or equivalent product"
    )
    equivalence_level: EquivalenceLevel = Field(
        default=EquivalenceLevel.UNVERIFIED,
        description="Level of clinical/pharmaceutical equivalence"
    )
    equivalence_notes: str = Field(description="Clinical notes detailing active ingredient, strength, and form match")
    price_difference: Optional[float] = Field(default=None, description="Absolute price difference in INR (₹)")
    savings_percentage: Optional[float] = Field(default=None, description="Percentage savings if generic is used")
    is_verified: bool = Field(default=True, description="Whether equivalent product and pricing were reliably verified")
    verification_message: Optional[str] = Field(
        default=None,
        description="Status message e.g. 'Equivalent product could not be reliably verified.'"
    )


class CostSaverAnalysisResult(BaseModel):
    session_id: str = Field(default="default", description="Active session ID")
    total_prescribed_cost: float = Field(default=0.0, description="Total cost of prescribed branded medicines in INR (₹)")
    potential_generic_cost: float = Field(default=0.0, description="Estimated total cost if generic equivalents are used in INR (₹)")
    total_potential_savings: float = Field(default=0.0, description="Total potential cost savings in INR (₹)")
    savings_percentage: float = Field(default=0.0, description="Overall savings percentage")
    comparisons: List[MedicineComparison] = Field(default_factory=list, description="Per-medicine price comparisons")
    data_source: str = Field(
        default="Pradhan Mantri Bhartiya Janaushadhi Pariyojana (PMBJP) / National Pharmaceutical Pricing Authority (NPPA)",
        description="Authoritative pricing and equivalence data provider"
    )
    price_timestamp: str = Field(default="2026-09-01T00:00:00Z", description="Effective date of pricing database")
    disclaimer: str = Field(
        default="Important: Do not change or substitute the prescribed medicine without consulting your doctor or pharmacist. Price comparisons are provided for patient informational awareness only.",
        description="Mandatory clinical safety notice"
    )


class CostSaverQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"
    document_ids: Optional[List[str]] = None


class CostSaverQuestionResponse(BaseModel):
    question: str
    answer: str
    comparisons: List[MedicineComparison] = []
    total_potential_savings: float = 0.0
    disclaimer: str = "Important: Do not change or substitute the prescribed medicine without consulting your doctor or pharmacist."


class CheckMedicineCostRequest(BaseModel):
    medicine_name: str
