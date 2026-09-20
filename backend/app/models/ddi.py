from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DDIInteractionRequest(BaseModel):
    document_ids: Optional[List[str]] = Field(default=None, alias="documentIds")
    user_id: Optional[str] = Field(default=None, alias="userId")

    class Config:
        populate_by_name = True


class DDIInteraction(BaseModel):
    medicine_a: str = Field(alias="medicineA")
    medicine_b: str = Field(alias="medicineB")
    interaction_description: str = Field(alias="interactionDescription")
    severity: Optional[str] = None
    category: Optional[str] = None
    source: str
    warning: str
    recommendation: str

    class Config:
        populate_by_name = True


class NormalizedMedicine(BaseModel):
    original_name: str = Field(alias="originalName")
    normalized_name: Optional[str] = Field(default=None, alias="normalizedName")
    rxcui: Optional[str] = None
    source_document_ids: List[str] = Field(default_factory=list, alias="sourceDocumentIds")
    status: str
    message: Optional[str] = None

    class Config:
        populate_by_name = True


class DDIInteractionResponse(BaseModel):
    medicines: List[NormalizedMedicine] = Field(default_factory=list)
    interactions: List[DDIInteraction] = Field(default_factory=list)
    unresolved_medicines: List[str] = Field(default_factory=list, alias="unresolvedMedicines")
    database_status: str = Field(alias="databaseStatus")
    message: str
    disclaimer: str

    class Config:
        populate_by_name = True
