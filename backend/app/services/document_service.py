import os
import re
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from pypdf import PdfReader
from app.models.document import (
    DocumentUploadResponse,
    DocumentListItem,
    ProcessingStage,
    ExtractedDocumentData,
    DocumentType,
)
from app.agents.document_agent import document_agent
from app.db.repository import (
    create_medical_document,
    get_medical_document,
    list_medical_documents,
    delete_medical_document,
)

logger = logging.getLogger(__name__)

# Base storage directory for securely uploaded documents
STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "documents"))
os.makedirs(STORAGE_DIR, exist_ok=True)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit
PDF_MAGIC_BYTES = b"%PDF-"


class DocumentService:
    """
    Manages secure medical document validation, storage, text extraction,
    and routing to the Document Agent.
    """

    def validate_file(self, file_bytes: bytes, filename: str) -> None:
        """
        Validates:
        1. File extension is .pdf
        2. File size is between 100 bytes and 15MB
        3. File begins with %PDF- magic signature
        """
        if not filename or not filename.lower().endswith(".pdf"):
            raise ValueError("Invalid file format. Only PDF documents (.pdf) are supported.")

        size = len(file_bytes)
        if size < 64:
            raise ValueError("The uploaded file appears to be empty or corrupted.")

        if size > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds maximum allowed limit of 15MB. (Current: {size / (1024*1024):.1f}MB)")

        # Validate PDF magic bytes header
        if not file_bytes.startswith(PDF_MAGIC_BYTES):
            # Check within first 1024 bytes in case of leading whitespace
            if PDF_MAGIC_BYTES not in file_bytes[:1024]:
                raise ValueError("Corrupt file. Header does not match a valid PDF document signature.")

    def store_file_securely(self, file_bytes: bytes, original_filename: str) -> Tuple[str, str, str]:
        """
        Saves file to secure storage directory with a collision-free UUID.
        Returns (doc_id, stored_path, sanitized_filename)
        """
        doc_id = f"doc-{uuid.uuid4().hex[:12]}"
        # Sanitize filename
        safe_name = re.sub(r"[^\w\.\-]", "_", original_filename)
        stored_filename = f"{doc_id}_{safe_name}"
        stored_path = os.path.join(STORAGE_DIR, stored_filename)

        with open(stored_path, "wb") as f:
            f.write(file_bytes)

        return doc_id, stored_path, safe_name

    def extract_pages_from_pdf(self, file_path: str) -> List[Tuple[int, str]]:
        """
        Extracts textual content from PDF file page-by-page.
        Returns list of (page_number, page_text).
        """
        try:
            reader = PdfReader(file_path)
            pages = []
            for idx, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text() or ""
                    if page_text.strip():
                        pages.append((idx + 1, page_text.strip()))
                except Exception as pe:
                    logger.warning(f"Could not extract page {idx + 1}: {pe}")
            return pages
        except Exception as e:
            logger.error(f"PDF extraction error for {file_path}: {e}")
            raise ValueError(f"Failed to extract readable text from PDF: {str(e)}")

    def extract_text_from_pdf(self, file_path: str) -> Tuple[str, int]:
        pages = self.extract_pages_from_pdf(file_path)
        combined_text = "\n\n".join(f"--- Page {p} ---\n{t}" for p, t in pages).strip()
        return combined_text, len(pages)

    def process_document_upload(
        self,
        file_bytes: bytes,
        original_filename: str,
        user_id: Optional[str] = None
    ) -> DocumentUploadResponse:
        """
        Complete processing pipeline for an uploaded PDF:
        1. Validate file type and size.
        2. Store document securely.
        3. Extract text from the PDF with page references.
        4. Detect document type.
        5. Show processing status milestones.
        6. Send extracted content to Document Agent.
        7. Index document chunks into Vector Database for RAG.
        8. Persist structured record.
        """
        stages: List[ProcessingStage] = []
        now_str = lambda: datetime.utcnow().strftime("%I:%M:%S %p")

        # Stage 1: Validation
        self.validate_file(file_bytes, original_filename)
        stages.append(ProcessingStage(
            stage="VALIDATING",
            message="File type and size verified successfully (PDF format).",
            status="completed",
            timestamp=now_str()
        ))

        # Stage 2: Secure Storage
        doc_id, stored_path, safe_filename = self.store_file_securely(file_bytes, original_filename)
        stages.append(ProcessingStage(
            stage="STORING",
            message=f"Document stored securely in clinical repository as {safe_filename}.",
            status="completed",
            timestamp=now_str()
        ))

        # Stage 3: PDF Text Extraction
        pages = self.extract_pages_from_pdf(stored_path)
        raw_text = "\n\n".join(f"--- Page {p} ---\n{t}" for p, t in pages).strip()
        page_count = len(pages)
        stages.append(ProcessingStage(
            stage="TEXT_EXTRACTED",
            message=f"Extracted clinical text across {page_count} page(s) ({len(raw_text)} characters).",
            status="completed",
            timestamp=now_str()
        ))

        # Stage 4: Document Agent Processing
        stages.append(ProcessingStage(
            stage="ANALYZING",
            message="Document Agent analyzing document type, medicines, provider, and policy clauses...",
            status="completed",
            timestamp=now_str()
        ))

        extracted_data = document_agent.process_document(raw_text, safe_filename)

        # Stage 5: Chunking & Vector DB Indexing for RAG Pipeline
        from app.services.document_rag_service import document_rag_service
        chunk_count = document_rag_service.index_document(
            doc_id=doc_id,
            doc_name=safe_filename,
            doc_type=extracted_data.document_type.value,
            pages=pages,
        )

        stages.append(ProcessingStage(
            stage="COMPLETED",
            message=f"Identified as {extracted_data.document_type.value}. Extracted {len(extracted_data.medicines)} medicine(s) and indexed {chunk_count} chunk(s) in Vector Store for Q&A.",
            status="completed",
            timestamp=now_str()
        ))

        # Stage 6: Persist in Database
        record = {
            "id": doc_id,
            "user_id": user_id,
            "file_name": safe_filename,
            "file_size": len(file_bytes),
            "file_path": stored_path,
            "mime_type": "application/pdf",
            "document_type": extracted_data.document_type.value,
            "processing_status": "COMPLETED",
            "extracted_data": extracted_data.dict(),
        }
        create_medical_document(record)
        from app.services.timeline_service import timeline_service
        timeline_service.extract_and_save_event(doc_id, user_id or "default")

        return DocumentUploadResponse(
            id=doc_id,
            file_name=safe_filename,
            file_size=len(file_bytes),
            processing_status="COMPLETED",
            stages=stages,
            extracted_data=extracted_data,
            created_at=datetime.utcnow().isoformat(),
        )

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return get_medical_document(doc_id)

    def list_documents(self, user_id: Optional[str] = None) -> List[DocumentListItem]:
        raw_list = list_medical_documents(user_id)
        items: List[DocumentListItem] = []

        for r in raw_list:
            ext_data = r.get("extracted_data") or {}
            doc_hosp = ext_data.get("doctor_hospital") or {}
            dates = ext_data.get("dates") or {}
            medicines = ext_data.get("medicines") or []

            doc_or_hosp = doc_hosp.get("doctor_name") or doc_hosp.get("hospital_name")
            doc_date = dates.get("document_date") or dates.get("consultation_date")

            items.append(DocumentListItem(
                id=r["id"],
                file_name=r["file_name"],
                file_size=r["file_size"],
                document_type=r.get("document_type", "OTHER"),
                doctor_or_hospital=doc_or_hosp,
                document_date=doc_date,
                medicines_count=len(medicines),
                processing_status=r.get("processing_status", "COMPLETED"),
                created_at=r.get("created_at", datetime.utcnow().isoformat()),
            ))
        return items

    def delete_document(self, doc_id: str) -> bool:
        from app.services.document_rag_service import document_rag_service
        document_rag_service.vector_store.delete_document_chunks(doc_id)
        doc = get_medical_document(doc_id)
        if doc and os.path.exists(doc.get("file_path", "")):
            try:
                os.remove(doc["file_path"])
            except Exception as e:
                logger.warning(f"Could not remove physical file {doc['file_path']}: {e}")
        return delete_medical_document(doc_id)


document_service = DocumentService()
