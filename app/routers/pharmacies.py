from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from app.models.pharmacy import (
    MedicineSearchRequest,
    MedicineSearchResponse,
)
from app.agents.medicine_search_agent import medicine_search_agent
from app.services.pharmacy_service import pharmacy_service

router = APIRouter(prefix="/api/pharmacies", tags=["Medicine & Pharmacy Search"])


@router.post("/search", response_model=MedicineSearchResponse)
async def search_medicines_and_pharmacies(request: MedicineSearchRequest) -> MedicineSearchResponse:
    """
    Medicine Search Agent Endpoint:
    - Reads medicines from an uploaded prescription OR explicit extracted list.
    - Retrieves public pharmacological details.
    - Discovers nearby verified pharmacies sorted by proximity in user's area.
    - Never recommends, changes dosage, or substitutes medicines.
    """
    try:
        if request.doc_id:
            return medicine_search_agent.search_for_document(
                doc_id=request.doc_id,
                locality=request.locality,
                lat=request.latitude,
                lng=request.longitude,
            )
        elif request.medicines:
            return medicine_search_agent.search_explicit_medicines(
                medicines=request.medicines,
                locality=request.locality,
                lat=request.latitude,
                lng=request.longitude,
            )
        else:
            # Default to latest uploaded document
            return medicine_search_agent.search_for_document(
                doc_id=None,
                locality=request.locality,
                lat=request.latitude,
                lng=request.longitude,
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing medicine search: {str(e)}"
        )


@router.get("/document/{doc_id}", response_model=MedicineSearchResponse)
async def search_pharmacies_for_document(
    doc_id: str,
    locality: Optional[str] = Query(default=None, description="Manually selected locality e.g. Koramangala"),
    lat: Optional[float] = Query(default=None, description="User latitude"),
    lng: Optional[float] = Query(default=None, description="User longitude"),
) -> MedicineSearchResponse:
    """
    1-Click pharmacy search for a specific uploaded prescription document.
    """
    try:
        return medicine_search_agent.search_for_document(
            doc_id=doc_id,
            locality=locality,
            lat=lat,
            lng=lng,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching pharmacies for document: {str(e)}"
        )


@router.get("/localities")
async def get_popular_localities() -> List[Dict[str, Any]]:
    """Returns Bengaluru localities for manual area selection."""
    return pharmacy_service.get_supported_localities()
