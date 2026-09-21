from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from app.services.cost_saver_service import cost_saver_service
from app.models.cost_saver import (
    CostSaverAnalysisResult,
    CostSaverQuestionRequest,
    CostSaverQuestionResponse,
    CheckMedicineCostRequest,
    MedicineComparison,
)

router = APIRouter(prefix="/api/cost-saver", tags=["Generic Medicine & Cost-Saver"])


@router.get("/latest", response_model=CostSaverAnalysisResult)
async def get_latest_cost_analysis(session_id: Optional[str] = "default"):
    """
    Returns generic medicine and cost-saver analysis across all uploaded prescriptions.
    """
    try:
        result = cost_saver_service.analyze_prescriptions_cost(session_id=session_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze", response_model=CostSaverAnalysisResult)
async def analyze_documents_cost(
    document_ids: Optional[List[str]] = None,
    session_id: Optional[str] = "default"
):
    """
    Analyzes specific prescription documents for generic options and price savings.
    """
    try:
        result = cost_saver_service.analyze_prescriptions_cost(
            session_id=session_id,
            document_ids=document_ids
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-medicine", response_model=MedicineComparison)
async def check_medicine_generic(req: CheckMedicineCostRequest):
    """
    Looks up a single prescribed medicine in the Jan Aushadhi / NPPA database.
    """
    try:
        comparison = cost_saver_service.evaluate_medicine_comparison(req.medicine_name)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=CostSaverQuestionResponse)
async def query_cost_saver(req: CostSaverQuestionRequest):
    """
    Natural language Q&A about generic options and price comparisons with strict clinical grounding.
    """
    try:
        res = cost_saver_service.answer_cost_query(req.question, session_id=req.session_id or "default")
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
