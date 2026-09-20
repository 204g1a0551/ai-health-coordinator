from fastapi import APIRouter, HTTPException, status

from app.models.ddi import DDIInteractionRequest, DDIInteractionResponse
from app.services.ddi_service import ddi_service

router = APIRouter(prefix="/api/ddi", tags=["Drug-Drug Interactions"])


@router.post("/check", response_model=DDIInteractionResponse)
async def check_drug_interactions(request: DDIInteractionRequest) -> DDIInteractionResponse:
    try:
        return ddi_service.check_documents(
            document_ids=request.document_ids,
            user_id=request.user_id,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Drug interaction information could not be verified: {exc}",
        )
