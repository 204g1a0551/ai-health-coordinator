import os
import re
import uuid
import logging
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException, status
from pypdf import PdfReader

from app.models.lab_report import (
    LabTestResult,
    LabReportData,
    LabQuestionRequest,
    LabQuestionResponse,
    LabEvidenceResponse,
)
from app.services.lab_report_service import LabReportService
from app.agents.lab_agent import lab_agent
from app.db.repository import (
    create_medical_document,
    get_medical_document,
    list_medical_documents,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lab-reports", tags=["Lab Reports Intelligence"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))
os.makedirs(STORAGE_DIR, exist_ok=True)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"
lab_service = LabReportService()


@router.post("/upload", response_model=LabReportData)
async def upload_lab_report(
    file: UploadFile = File(...),
    patient_name: Optional[str] = Form(None),
):
    """
    Upload a laboratory report in PDF format:
    1. Validate PDF structure and integrity.
    2. Document Agent detects whether the document is a lab report.
    3. Extracts: Test name, Result, Unit, Reference range, Report date, Laboratory name.
    4. Identifies values outside stated reference ranges (non-diagnostic).
    """
    filename = file.filename or "lab_report.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF laboratory reports (.pdf) are supported.",
        )

    content = await file.read()
    if len(content) < 64:
        raise HTTPException(status_code=400, detail="The uploaded lab file is empty or corrupted.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit of 15MB.")
    if not content.startswith(PDF_MAGIC_BYTES) and PDF_MAGIC_BYTES not in content[:1024]:
        raise HTTPException(status_code=400, detail="File header does not match a valid PDF document signature.")

    # Save to storage
    doc_id = f"doc-{uuid.uuid4().hex[:12]}"
    safe_name = re.sub(r"[^\w\.\-]", "_", filename)
    stored_path = os.path.join(STORAGE_DIR, f"{doc_id}_{safe_name}")

    with open(stored_path, "wb") as f:
        f.write(content)

    # Extract text to verify and classify
    try:
        reader = PdfReader(stored_path)
        extracted_pages = []
        full_text = ""
        for p in reader.pages:
            t = p.extract_text() or ""
            extracted_pages.append(t)
            full_text += "\n" + t
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        extracted_pages = [""]
        full_text = ""

    # Document Agent classification: Is it a lab report?
    is_lab, confidence = lab_service.detect_lab_report(full_text, filename)

    # Register in repository
    doc_metadata = {
        "id": doc_id,
        "file_name": safe_name,
        "file_path": stored_path,
        "file_size": len(content),
        "document_type": "LAB_REPORT" if is_lab else "MEDICAL_REPORT",
        "is_lab_report": is_lab,
        "lab_detection_confidence": confidence,
        "page_count": len(extracted_pages),
        "uploaded_at": "2026-09-20T22:00:00Z",
    }
    create_medical_document(doc_metadata)

    # Parse report data
    report_data = lab_service.get_report_data(doc_id)
    if patient_name:
        report_data.patient_name = patient_name

    return report_data


@router.get("/latest", response_model=LabReportData)
def get_latest_lab_report():
    """Retrieve the latest uploaded laboratory report."""
    return lab_service.get_latest_lab_report()


@router.get("/{document_id}", response_model=LabReportData)
def get_lab_report_by_id(document_id: str):
    """Retrieve a specific laboratory report by ID."""
    return lab_service.get_report_data(document_id)


@router.post("/query", response_model=LabQuestionResponse)
def query_lab_report(req: LabQuestionRequest):
    """
    RAG Question & Answer grounded strictly on the laboratory report.
    Answers:
    - What tests are in this report?
    - Which values are outside the reference range?
    - What does page 3 say?
    - Show my latest lab report.
    """
    return lab_service.answer_lab_query(req.question, req.document_id)


@router.get("/{document_id}/evidence", response_model=LabEvidenceResponse)
def get_lab_evidence(
    document_id: str,
    page: int = Query(1, ge=1, le=20),
    query: str = Query("", description="Optional search query"),
):
    """Retrieve page-grounded laboratory evidence with extracted text and relevant tests."""
    return lab_service.get_page_evidence(page_num=page, query=query, doc_id=document_id)
