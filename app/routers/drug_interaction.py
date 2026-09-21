from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.ddi_service import ddi_service
from app.models.drug_interaction import (
    DDIAnalysisResult,
    DDIQuestionRequest,
    DDIQuestionResponse,
    CheckPairRequest,
    DrugInteractionPair,
    NormalizedMedication,
)

router = APIRouter(prefix="/api/ddi", tags=["Drug-Drug Interaction Checker"])


@router.get("/latest", response_model=DDIAnalysisResult)
async def get_latest_interaction_analysis(session_id: Optional[str] = "default"):
    """
    Analyzes and returns potential drug-drug interactions across all uploaded
    prescriptions and clinical documents in the active session.
    """
    try:
        result = ddi_service.analyze_cross_prescription_interactions(session_id=session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=DDIAnalysisResult)
async def analyze_documents_interaction(
    document_ids: Optional[List[str]] = None,
    session_id: Optional[str] = "default"
):
    """
    Analyzes specific uploaded documents for drug-drug interactions.
    """
    try:
        result = ddi_service.analyze_cross_prescription_interactions(
            session_id=session_id,
            document_ids=document_ids
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-pair", response_model=DrugInteractionPair)
async def check_specific_pair(req: CheckPairRequest):
    """
    Directly checks an individual pair of medicines for interactions.
    Normalizes names via RxNorm before checking.
    """
    try:
        med_a = ddi_service.normalize_medicine_name(req.medicine_a)
        med_b = ddi_service.normalize_medicine_name(req.medicine_b)
        pair = ddi_service.check_interaction_pair(med_a, med_b)
        return pair
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=DDIQuestionResponse)
async def query_interaction(req: DDIQuestionRequest):
    """
    Natural language question-answering on drug interactions with strict grounding.
    """
    try:
        res = ddi_service.answer_interaction_query(req.question, session_id=req.session_id or "default")
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
