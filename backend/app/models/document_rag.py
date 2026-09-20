from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentReference(BaseModel):
    doc_id: str
    doc_name: str
    page_number: int
    snippet: str
    similarity_score: float = Field(default=0.0, description="Cosine similarity score (0.0 to 1.0)")


class DocumentQuestionRequest(BaseModel):
    doc_id: Optional[str] = Field(default=None, description="Specific document ID to query. If None, queries across all uploaded documents.")
    question: str = Field(..., description="User natural-language question regarding medical document")
    session_id: Optional[str] = Field(default=None, description="Optional chat session ID for context")


class DocumentAnswerResponse(BaseModel):
    question: str
    answer: str
    found_in_document: bool = Field(default=True, description="False if information could not be found in document")
    document_id: Optional[str] = None
    document_name: Optional[str] = None
    document_type: Optional[str] = None
    references: List[DocumentReference] = Field(default_factory=list, description="Document excerpts and page citations")
    extracted_entities: Optional[Dict[str, Any]] = Field(default=None, description="Grounded entities extracted relevant to query")
    disclaimer: str = Field(
        default="Important: This information is extracted directly from the uploaded document for reference and does not constitute independent medical advice or a diagnosis.",
        description="Clinical disclaimer"
    )
