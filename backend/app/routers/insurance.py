import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from pypdf import PdfReader

from app.models.insurance import (
    PolicyUploadCategory,
    ExtractedPolicyRules,
    CoverageComparisonRequest,
    CoverageComparisonResponse,
    PolicyQuestionRequest,
    PolicyAnswerResponse,
)
from app.services.insurance_rag_service import insurance_rag_service
from app.agents.insurance_agent import insurance_agent
from app.db.repository import (
    create_medical_document,
    get_medical_document,
    list_medical_documents,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/insurance", tags=["Insurance & Reimbursement"])

STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))
os.makedirs(STORAGE_DIR, exist_ok=True)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF-"


@router.post("/upload")
async def upload_insurance_policy(
    file: UploadFile = File(...),
    category: PolicyUploadCategory = Form(PolicyUploadCategory.COMPANY_HEALTH_INSURANCE),
    user_id: Optional[str] = Form(None),
):
    """
    Upload and index a corporate health insurance or reimbursement policy:
    1. Validate PDF format and magic signature.
    2. Store file securely.
    3. Extract pages.
    4. Chunk and index into Policy Vector Store for RAG.
    5. Save metadata into repository.
    """
    filename = file.filename or "policy.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only PDF documents (.pdf) are supported.",
        )

    content = await file.read()
    if len(content) < 64:
        raise HTTPException(status_code=400, detail="The uploaded file appears to be empty or corrupted.")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File size exceeds maximum allowed limit of 15MB.")
    if not content.startswith(PDF_MAGIC_BYTES) and PDF_MAGIC_BYTES not in content[:1024]:
        raise HTTPException(status_code=400, detail="Header does not match a valid PDF document signature.")

    # Save to storage
    doc_id = f"policy-{uuid.uuid4().hex[:12]}"
    safe_name = re.sub(r"[^\w\.\-]", "_", filename)
    stored_path = os.path.join(STORAGE_DIR, f"{doc_id}_{safe_name}")

    with open(stored_path, "wb") as f:
        f.write(content)

    # Extract pages
    try:
        reader = PdfReader(stored_path)
        pages = []
        for idx, p in enumerate(reader.pages):
            txt = p.extract_text() or ""
            if txt.strip():
                pages.append((idx + 1, txt.strip()))
    except Exception as e:
        logger.error(f"Failed to extract PDF text from {stored_path}: {e}")
        pages = [(1, "Corporate Medical & Health Insurance Policy terms.")]

    # Chunk and index into Vector Store
    chunks_count = insurance_rag_service.index_policy_pages(
        policy_id=doc_id,
        policy_name=filename,
        category=category,
        pages=pages,
    )

    # Persist in DB
    doc_type = "INSURANCE_POLICY" if "insurance" in category.value.lower() else "REIMBURSEMENT_POLICY"
    doc_record = {
        "id": doc_id,
        "user_id": user_id or "user_default",
        "file_name": filename,
        "file_size": len(content),
        "file_path": stored_path,
        "mime_type": "application/pdf",
        "document_type": doc_type,
        "processing_status": "COMPLETED",
        "extracted_data": {
            "policy_category": category.value,
            "page_count": len(pages),
            "chunks_count": chunks_count,
        },
    }
    create_medical_document(doc_record)

    # Extract initial rules
    rules = insurance_agent.extract_rules(doc_id)

    return {
        "id": doc_id,
        "file_name": filename,
        "category": category.value,
        "page_count": len(pages),
        "chunks_indexed": chunks_count,
        "rules": rules.dict(),
    }


@router.get("/policies")
async def list_policies():
    """
    List all uploaded insurance policies and reimbursement guidelines.
    """
    all_docs = list_medical_documents()
    policy_docs = [
        d for d in all_docs
        if d.get("document_type") in ["INSURANCE_POLICY", "REIMBURSEMENT_POLICY"]
        or "policy" in d.get("file_name", "").lower()
    ]

    results = []
    for d in policy_docs:
        results.append({
            "id": d["id"],
            "file_name": d["file_name"],
            "file_size": d.get("file_size", 0),
            "document_type": d.get("document_type", "INSURANCE_POLICY"),
            "created_at": d.get("created_at", ""),
        })
    return results


@router.get("/policies/{policy_id}/rules", response_model=ExtractedPolicyRules)
async def get_policy_rules(policy_id: str):
    """
    Returns the 8-dimension extracted rules for the specified policy.
    """
    return insurance_agent.extract_rules(policy_id)


@router.post("/compare", response_model=CoverageComparisonResponse)
async def compare_medical_document(request: CoverageComparisonRequest):
    """
    Compares user's uploaded medical bill or prescription against policy.
    Returns grounded assessment, evidence citations, and conditions.
    """
    return insurance_agent.compare_coverage(
        policy_id=request.policy_id,
        medical_document_id=request.medical_document_id,
        user_query=request.user_query,
    )


@router.post("/query", response_model=PolicyAnswerResponse)
async def query_policy(request: PolicyQuestionRequest):
    """
    Interactive RAG question answering on policy terms.
    """
    return insurance_agent.answer_policy_inquiry(
        question=request.question,
        policy_id=request.policy_id,
    )
