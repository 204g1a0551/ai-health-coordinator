import os
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import FileResponse

from app.models.document import (
    DocumentUploadResponse,
    DocumentListItem,
    ExtractedDocumentData,
)
from app.services.document_service import document_service

router = APIRouter(prefix="/api/documents", tags=["Medical Documents"])


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
        return response
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the medical document: {str(e)}"
        )


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
    """Downloads the original stored PDF securely."""
    doc = document_service.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    file_path = doc.get("file_path", "")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Physical file not found on server")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc["file_name"],
    )


@router.delete("/{doc_id}")
async def delete_medical_document(doc_id: str):
    """Deletes document record and associated file."""
    success = document_service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found or already deleted")
    return {"message": "Document deleted successfully", "id": doc_id}
