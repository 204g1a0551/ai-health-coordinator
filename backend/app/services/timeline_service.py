import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.db.repository import get_db_connection, get_medical_document, init_db, list_medical_documents
from app.models.timeline import (
    ExpenseSummary,
    MedicalExpense,
    TimelineEvent,
    TimelineEventType,
    TimelineQueryResponse,
)
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


def _amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(value))
    return float(match.group(0).replace(",", "")) if match else None


class TimelineService:
    cache_ttl = 300

    def _classify(self, doc_type: str) -> TimelineEventType:
        return {
            "PRESCRIPTION": TimelineEventType.PRESCRIPTION,
            "DOCTOR_CONSULTATION": TimelineEventType.CONSULTATION,
            "MEDICAL_REPORT": TimelineEventType.LAB_REPORT,
            "LAB_REPORT": TimelineEventType.LAB_REPORT,
            "MEDICINE_BILL": TimelineEventType.PHARMACY_BILL,
            "INSURANCE_POLICY": TimelineEventType.INSURANCE,
            "REIMBURSEMENT_POLICY": TimelineEventType.INSURANCE,
        }.get(doc_type, TimelineEventType.FOLLOW_UP)

    def extract_and_save_event(self, doc_id: str, session_id: str) -> TimelineEvent:
        init_db()
        document = get_medical_document(doc_id)
        if not document:
            raise ValueError(f"Document not found: {doc_id}")
        data = document.get("extracted_data") or {}
        if isinstance(data, str):
            data = json.loads(data)
        doc_type = document.get("document_type", "OTHER")
        doctor_hospital = data.get("doctor_hospital") or {}
        dates = data.get("dates") or {}
        event_type = self._classify(doc_type)
        date = dates.get("consultation_date") or dates.get("document_date") or document.get("created_at")
        medicines = [m.get("name", "").strip() for m in data.get("medicines", []) if m.get("name")]
        total = _amount(data.get("total_amount"))
        event_id = f"{doc_id}:{session_id}"
        summary = data.get("clinical_notes_summary") or f"{event_type.value.replace('_', ' ').title()} from {document.get('file_name', 'document')}."
        event = TimelineEvent(
            event_id=event_id,
            session_id=session_id,
            event_type=event_type,
            date=date,
            doctor=doctor_hospital.get("doctor_name"),
            hospital=doctor_hospital.get("hospital_name"),
            medicines=medicines,
            bill_amount=total if event_type == TimelineEventType.PHARMACY_BILL else None,
            consultation_amount=total if event_type == TimelineEventType.CONSULTATION else None,
            diagnostic_amount=total if event_type == TimelineEventType.LAB_REPORT else None,
            doc_id=doc_id,
            doc_type=doc_type,
            summary=summary[:500],
            created_at=datetime.utcnow().isoformat(),
        )
        conn = get_db_connection()
        conn.execute(
            """INSERT OR REPLACE INTO medical_timeline_events
            (event_id, session_id, event_type, date, doctor, hospital, medicines,
             bill_amount, consultation_amount, diagnostic_amount, doc_id, doc_type, summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (event.event_id, event.session_id, event.event_type.value, event.date, event.doctor,
             event.hospital, json.dumps(event.medicines), event.bill_amount, event.consultation_amount,
             event.diagnostic_amount, event.doc_id, event.doc_type, event.summary, event.created_at),
        )
        conn.commit()
        conn.close()
        if total is not None:
            category = "medicine" if event_type == TimelineEventType.PHARMACY_BILL else (
                "consultation" if event_type == TimelineEventType.CONSULTATION else
                "diagnostic" if event_type == TimelineEventType.LAB_REPORT else "insurance"
            )
            conn = get_db_connection()
            conn.execute(
                """INSERT OR REPLACE INTO medical_expenses
                (expense_id, session_id, category, amount, date, provider, doc_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (event_id, session_id, category, total, date,
                 doctor_hospital.get("hospital_name") or doctor_hospital.get("doctor_name"), doc_id),
            )
            conn.commit()
            conn.close()
        self._invalidate(session_id)
        return event

    def _invalidate(self, session_id: str) -> None:
        redis_service.delete_timeline_cache(session_id)

    def _row_event(self, row: Any) -> TimelineEvent:
        return TimelineEvent(
            event_id=row["event_id"], session_id=row["session_id"],
            event_type=row["event_type"], date=row["date"], doctor=row["doctor"],
            hospital=row["hospital"], medicines=json.loads(row["medicines"] or "[]"),
            bill_amount=row["bill_amount"], consultation_amount=row["consultation_amount"],
            diagnostic_amount=row["diagnostic_amount"], doc_id=row["doc_id"],
            doc_type=row["doc_type"], summary=row["summary"], created_at=row["created_at"],
        )

    def get_timeline(self, session_id: str) -> List[TimelineEvent]:
        cached = redis_service.get_timeline_cache(session_id)
        if cached is not None:
            return [TimelineEvent(**item) for item in cached]
        init_db()
        conn = get_db_connection()
        rows = conn.execute(
            "SELECT * FROM medical_timeline_events WHERE session_id = ? ORDER BY date DESC, created_at DESC",
            (session_id,),
        ).fetchall()
        conn.close()
        events = [self._row_event(row) for row in rows]
        if not events:
            for doc in list_medical_documents(session_id):
                if doc.get("processing_status") == "COMPLETED":
                    self.extract_and_save_event(doc["id"], session_id)
            conn = get_db_connection()
            rows = conn.execute(
                "SELECT * FROM medical_timeline_events WHERE session_id = ? ORDER BY date DESC, created_at DESC",
                (session_id,),
            ).fetchall()
            conn.close()
            events = [self._row_event(row) for row in rows]
        redis_service.set_timeline_cache(session_id, [e.dict() for e in events], self.cache_ttl)
        return events

    def get_expenses(self, session_id: str, period: Optional[str] = None) -> ExpenseSummary:
        init_db()
        conn = get_db_connection()
        query = "SELECT * FROM medical_expenses WHERE session_id = ?"
        params: List[Any] = [session_id]
        if period == "month":
            query += " AND substr(date, 1, 7) = ?"
            params.append(datetime.utcnow().strftime("%Y-%m"))
        rows = conn.execute(query, params).fetchall()
        conn.close()
        expenses = [MedicalExpense(**dict(row)) for row in rows]
        totals: Dict[str, float] = {}
        monthly: Dict[str, Dict[str, float]] = {}
        for expense in expenses:
            totals[expense.category] = round(totals.get(expense.category, 0) + expense.amount, 2)
            month = (expense.date or "Unknown")[:7]
            monthly.setdefault(month, {})[expense.category] = round(monthly.setdefault(month, {}).get(expense.category, 0) + expense.amount, 2)
        return ExpenseSummary(expenses=expenses, category_totals=totals, monthly_breakdown=monthly, total=round(sum(totals.values()), 2))

    def answer_timeline_query(self, session_id: str, question: str) -> TimelineQueryResponse:
        events = self.get_timeline(session_id)
        words = set(re.findall(r"\w+", question.lower()))
        relevant = [event for event in events if words.intersection(set(re.findall(r"\w+", f"{event.event_type.value} {event.summary} {event.doctor or ''} {event.hospital or ''}")))]
        selected = relevant or events[:5]
        if not selected:
            return TimelineQueryResponse(events=[], summary="I could not find any uploaded medical events for this session.", evidence=[])
        latest = selected[0]
        summary = f"The most relevant recorded event is {latest.event_type.value.replace('_', ' ').title()} on {latest.date or 'an unspecified date'}."
        return TimelineQueryResponse(
            events=selected,
            summary=summary,
            evidence=[{"doc_id": e.doc_id, "doc_type": e.doc_type, "date": e.date} for e in selected],
        )


timeline_service = TimelineService()
