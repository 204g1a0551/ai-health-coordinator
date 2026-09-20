from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MedicineInfo(BaseModel):
    name: str = Field(description="Prescription medicine name")
    generic_name: str = Field(description="Active pharmacological/generic substance")
    therapeutic_class: str = Field(description="Therapeutic/clinical classification")
    common_usage_category: str = Field(description="General public category of use")
    form: str = Field(default="Oral Tablet", description="Form of medication e.g. Tablet, Syrup, Capsule")
    storage_instructions: str = Field(default="Store in a cool, dry place away from direct light", description="Storage instructions")
    schedule: str = Field(default="Schedule H (Prescription Required)", description="Drug regulatory classification")
    disclaimer: str = Field(
        default="Public pharmacological information for reference only. Do not alter dosage, substitute, or self-medicate.",
        description="Safety notice"
    )


class PharmacyStore(BaseModel):
    id: str
    name: str
    chain: str
    locality: str
    address: str
    distance_km: float
    phone: str
    timing: str
    is_open: bool = True
    rating: float = 4.8
    in_stock_medicines: List[str] = Field(default_factory=list, description="Medicines from prescription verified in stock")
    latitude: float
    longitude: float


from pydantic import BaseModel, Field, ConfigDict


class MedicineSearchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    doc_id: Optional[str] = Field(default=None, alias="document_id", description="Document ID to load medicines from")
    medicines: Optional[List[str]] = Field(default=None, alias="explicit_medicines", description="Explicit medicine names to search")
    locality: Optional[str] = Field(default=None, description="Manually entered locality (e.g. Koramangala)")
    latitude: Optional[float] = Field(default=None, alias="lat", description="User latitude if location permission granted")
    longitude: Optional[float] = Field(default=None, alias="lng", description="User longitude if location permission granted")


class MedicineSearchResponse(BaseModel):
    medicines_searched: List[str]
    medicine_details: List[MedicineInfo]
    location_searched: str
    pharmacies: List[PharmacyStore]
    total_pharmacies_found: int
    disclaimer: str = Field(
        default="Notice: Pharmacy search is provided for coordination and availability tracking of explicitly prescribed medicines only. The system does not recommend, change dosage, or substitute medications.",
        description="Clinical disclaimer"
    )
