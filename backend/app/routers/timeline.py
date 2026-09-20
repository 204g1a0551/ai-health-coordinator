from typing import Optional

from fastapi import APIRouter, Body, HTTPException, Query

from app.models.timeline import ExpenseSummary, TimelineQueryResponse
from app.services.timeline_service import timeline_service

router = APIRouter(prefix="/api/timeline", tags=["Medical Timeline"])


@router.get("")
async def get_timeline(session_id: str = Query("default")):
    return {"events": timeline_service.get_timeline(session_id)}


@router.get("/expenses", response_model=ExpenseSummary)
async def get_expenses(session_id: str = Query("default"), period: Optional[str] = None):
    if period not in (None, "month"):
        raise HTTPException(status_code=400, detail="period must be 'month' or omitted")
    return timeline_service.get_expenses(session_id, period)


@router.get("/history")
async def get_document_history(session_id: str = Query("default")):
    events = timeline_service.get_timeline(session_id)
    return {
        "documents": [
            {
                "doc_id": event.doc_id,
                "doc_type": event.doc_type,
                "date": event.date,
                "doctor": event.doctor,
                "hospital": event.hospital,
                "file_name": event.summary,
            }
            for event in events
        ]
    }


@router.post("/query", response_model=TimelineQueryResponse)
async def query_timeline(payload: dict = Body(...)):
    session_id = str(payload.get("session_id") or "default")
    question = str(payload.get("question") or "")
    if not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    return timeline_service.answer_timeline_query(session_id, question)
