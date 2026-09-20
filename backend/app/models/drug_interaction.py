from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class InteractionSeverity(str, Enum):
    HIGH = "HIGH"
    MAJOR = "MAJOR"
    MODERATE = "MODERATE"
    MINOR = "MINOR"
    UNVERIFIED = "UNVERIFIED"


class NormalizedMedication(BaseModel):
    raw_name: str = Field(description="Original medicine text from prescription or document")
    normalized_name: str = Field(description="Standardized active ingredient / generic substance name")
    brand_name: Optional[str] = Field(default=None, description="Identified commercial brand name if applicable")
    rxnorm_id: Optional[str] = Field(default=None, description="Standard RxNorm Concept Identifier (CUI)")
    dosage: Optional[str] = Field(default=None, description="Prescribed dose as written")
    frequency: Optional[str] = Field(default=None, description="Prescribed frequency as written")
    source_document_id: Optional[str] = Field(default=None, description="ID of source document")
    source_document_name: Optional[str] = Field(default=None, description="File name of source document")
    source_department: Optional[str] = Field(default=None, description="Prescribing clinical department (e.g. Cardiology, Orthopedics)")


class DrugInteractionPair(BaseModel):
    medicine_a: NormalizedMedication = Field(description="First participating medication")
    medicine_b: NormalizedMedication = Field(description="Second participating medication")
    severity: InteractionSeverity = Field(description="Clinical severity grade according to authoritative source")
    description: str = Field(description="Pharmacological interaction description and mechanism")
    clinical_effect: str = Field(description="Potential physiological or pharmacological effect")
    source: str = Field(description="Authoritative medical terminology/interaction data provider citation")
    warning: str = Field(description="Relevant safety warning for the interaction")
    recommendation: str = Field(
        default="Please consult your doctor or pharmacist before changing, stopping, or combining medicines.",
        description="Clinical safety recommendation"
    )
    is_verified: bool = Field(default=True, description="Whether interaction is confirmed in authoritative source")


class DDIAnalysisResult(BaseModel):
    session_id: str = Field(default="default", description="Active session ID")
    total_medications: int = Field(default=0, description="Total unique medications analyzed")
    medications: List[NormalizedMedication] = Field(default_factory=list, description="All normalized medications extracted")
    duplicate_medications: List[Dict[str, Any]] = Field(default_factory=list, description="Detected duplicate medications across documents")
    interactions_found: int = Field(default=0, description="Number of verified interactions found")
    interactions: List[DrugInteractionPair] = Field(default_factory=list, description="Identified drug-drug interaction pairs")
    unverified_pairs: List[DrugInteractionPair] = Field(default_factory=list, description="Pairs where interaction data could not be verified")
    sources_checked: List[str] = Field(default_factory=list, description="Authoritative sources checked")
    analyzed_documents: List[Dict[str, str]] = Field(default_factory=list, description="Documents included in analysis")
    analyzed_at: str = Field(description="ISO timestamp of analysis")
    disclaimer: str = Field(
        default="Clinical Safety Notice: Do not alter dosages, stop taking prescribed medication, or substitute medicines based on this automated check. Always consult your prescribing physician or pharmacist for clinical guidance.",
        description="Mandatory clinical safety notice"
    )


class DDIQuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default"
    document_ids: Optional[List[str]] = None


class DDIQuestionResponse(BaseModel):
    question: str
    answer: str
    interactions: List[DrugInteractionPair] = []
    medications: List[NormalizedMedication] = []
    disclaimer: str = "Please consult your doctor or pharmacist before changing, stopping, or combining medicines."


class CheckPairRequest(BaseModel):
    medicine_a: str
    medicine_b: str
