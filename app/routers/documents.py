import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from app.models.document import (
    DocumentUploadResponse,
    DocumentListItem,
    ExtractedDocumentData,
)
from app.models.document_rag import (
    DocumentQuestionRequest,
    DocumentAnswerResponse,
)
from app.services.document_service import document_service
from app.services.document_rag_service import document_rag_service

router = APIRouter(prefix="/api/documents", tags=["Medical Documents"])


@router.post("/qa", response_model=DocumentAnswerResponse)
async def ask_document_question(request: DocumentQuestionRequest) -> DocumentAnswerResponse:
    """
    Document Intelligence & RAG pipeline endpoint.
    Answers natural-language questions grounded strictly in the uploaded document:
    - 'What medicines are mentioned in this prescription?'
    - 'What is the prescribed dosage?'
    - 'What is the consultation date?'
    - 'What does my insurance policy say about outpatient medicines?'
    - 'Does my company policy mention pharmacy reimbursement?'
    Provides document references and page numbers for every answer.
    Never fabricates information.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty."
        )

    try:
        return document_rag_service.answer_question(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing document RAG pipeline: {str(e)}"
        )



@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_medical_document(
    file: UploadFile = File(..., description="Medical PDF file (prescription, report, policy, etc.)"),
    user_id: Optional[str] = Form(default=None),
) -> DocumentUploadResponse:
    """
    Accepts, validates, securely stores, and extracts structured entities from medical PDFs:
    - Supported types: Prescription, Doctor Consultation, Medical Report, Medicine Bill,
      Insurance Policy, Company Medical Reimbursement Policy.
    - Extracts: Medicines, Doctor/Hospital, Dates, Policy Clauses.
    - Guarantees: Never hallucinates or generates ungrounded medical claims.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A valid PDF file must be provided."
        )

    try:
        content = await file.read()
        response = document_service.process_document_upload(
            file_bytes=content,
            original_filename=file.filename,
            user_id=user_id
        )

        # Immutable Audit Trail: DOCUMENT_UPLOADED
        from app.security.audit_trail import audit_trail, AuditAction
        audit_trail.record_event(
            action=AuditAction.DOCUMENT_UPLOADED,
            user_id=user_id or "anonymous",
            resource_type="MEDICAL_DOCUMENT",
            resource_id=response.id,
            purpose="CARE_COORDINATION",
            result="SUCCESS",
            details=f"document_id={response.id} file_name={response.file_name}"
        )

        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the medical document: {str(e)}"
        )


from app.security.document_storage import validate_storage_path
from app.security.audit import audit_logger, SecurityEventType
from app.security.audit_trail import audit_trail, AuditAction
from app.services.document_service import STORAGE_DIR

@router.get("", response_model=List[DocumentListItem])
async def list_medical_documents(user_id: Optional[str] = None) -> List[DocumentListItem]:
    """Retrieves all uploaded medical documents and their extraction status."""
    return document_service.list_documents(user_id=user_id)


@router.get("/{doc_id}", response_model=DocumentUploadResponse)
async def get_medical_document_details(doc_id: str) -> DocumentUploadResponse:
    """Retrieves full details and extracted structured information for a specific document."""
    doc = document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Security Audit Log & Immutable Audit Trail: DOCUMENT_ACCESSED
    audit_logger.log_event(
        event_type=SecurityEventType.DOCUMENT_ACCESSED,
        actor_id=doc.get("user_id") or "anonymous",
        resource_id=doc_id,
        details=f"Accessed document metadata: {doc.get('file_name')}",
        severity="LOW"
    )
    audit_trail.record_event(
        action=AuditAction.DOCUMENT_ACCESSED,
        user_id=doc.get("user_id") or "anonymous",
        resource_type="MEDICAL_DOCUMENT",
        resource_id=doc_id,
        purpose="DOCUMENT_ANALYSIS",
        result="SUCCESS",
        details=f"document_id={doc_id} agent=DOCUMENT_AGENT"
    )

    ext_data = None
    if doc.get("extracted_data"):
        try:
            ext_data = ExtractedDocumentData(**doc["extracted_data"])
        except Exception:
            pass

    return DocumentUploadResponse(
        id=doc["id"],
        file_name=doc["file_name"],
        file_size=doc["file_size"],
        processing_status=doc.get("processing_status", "COMPLETED"),
        stages=[],
        extracted_data=ext_data,
        created_at=doc.get("created_at", ""),
    )


@router.get("/{doc_id}/download")
async def download_medical_document(doc_id: str):
    """Downloads the original stored PDF securely with path traversal protection."""
    doc = document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = doc.get("file_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file not found on server")

    # Path traversal validation
    validate_storage_path(STORAGE_DIR, file_path)

    # Security Audit Log & Immutable Audit Trail: DOCUMENT_DOWNLOADED
    audit_logger.log_event(
        event_type=SecurityEventType.DOCUMENT_ACCESSED,
        actor_id=doc.get("user_id") or "anonymous",
        resource_id=doc_id,
        details=f"Downloaded binary file: {doc.get('file_name')}",
        severity="LOW"
    )
    audit_trail.record_event(
        action=AuditAction.DOCUMENT_DOWNLOADED,
        user_id=doc.get("user_id") or "anonymous",
        resource_type="MEDICAL_DOCUMENT",
        resource_id=doc_id,
        purpose="RECORDS_ACCESS",
        result="SUCCESS",
        details=f"document_id={doc_id} format=PDF"
    )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc["file_name"],
    )


@router.delete("/{doc_id}")
async def delete_medical_document(doc_id: str):
    """Deletes document record and associated file."""
    doc = document_service.get_document(doc_id)
    success = document_service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or already deleted")

    # Security Audit Log & Immutable Audit Trail: DOCUMENT_DELETED
    audit_logger.log_event(
        event_type=SecurityEventType.DOCUMENT_ERASED,
        actor_id=doc.get("user_id") if doc else "anonymous",
        resource_id=doc_id,
        details=f"Deleted document {doc_id}",
        severity="MEDIUM"
    )
    audit_trail.record_event(
        action=AuditAction.DOCUMENT_DELETED,
        user_id=doc.get("user_id") if doc else "anonymous",
        resource_type="MEDICAL_DOCUMENT",
        resource_id=doc_id,
        purpose="DATA_ERASURE",
        result="SUCCESS",
        details=f"document_id={doc_id}"
    )

    return {"message": "Document deleted successfully", "id": doc_id}
