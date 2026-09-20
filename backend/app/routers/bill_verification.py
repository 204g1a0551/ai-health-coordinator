from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
from app.services.bill_verification_service import bill_verification_service
from app.models.bill_verification import VerificationQuestionRequest

router = APIRouter(prefix="/api/bill-verification", tags=["Bill Verification"])


@router.post("/verify")
async def verify_documents(
    prescription_doc_id: str = Form(...),
    bill_doc_id: str = Form(...),
    session_id: Optional[str] = Form(None)
):
    """
    Compare a prescription document against a pharmacy bill.
    Returns a detailed comparison matrix with discrepancies.
    """
    try:
        result = await bill_verification_service.verify_documents(
            prescription_doc_id=prescription_doc_id,
            bill_doc_id=bill_doc_id,
            session_id=session_id
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_verification(session_id: Optional[str] = None):
    """
    Retrieve the most recent bill verification result for a session.
    """
    try:
        result = bill_verification_service.get_latest_verification(session_id)
        if not result:
            return {"success": False, "message": "No bill verification data found"}
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def answer_verification_query(request: VerificationQuestionRequest):
    """
    Answer a natural language question about a bill verification result.
    Supports RAG with document page references.
    """
    try:
        result = await bill_verification_service.answer_verification_query(
            session_id=request.session_id,
            question=request.question
        )
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence")
async def get_verification_evidence(session_id: Optional[str] = None):
    """
    Retrieve verification evidence with document page references.
    """
    try:
        result = bill_verification_service.get_verification_evidence(session_id)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
