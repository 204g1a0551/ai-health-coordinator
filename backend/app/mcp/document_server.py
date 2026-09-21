"""
Document MCP Server
Controlled access to processed medical documents, pages, chunk evidence, and metadata.
Includes strict prompt injection defense and per-user access control.
"""

import re
from typing import Any, Dict, List, Optional
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.db.repository import get_medical_document, list_medical_documents
from app.services.document_rag_service import document_rag_service


def sanitize_untrusted_document_content(text: str) -> str:
    """
    Sanitizes untrusted text extracted from medical PDFs.
    Neutralizes prompt injection patterns (system prompt overrides, instruction jailbreaks).
    Ensures document content is treated strictly as raw data rather than executable instructions.
    """
    if not text:
        return ""

    injection_patterns = [
        r"(?i)\bignore\s+(all\s+)?(previous|prior)\s+instructions\b",
        r"(?i)\bsystem\s+prompt\s*:\s*",
        r"(?i)\byou\s+are\s+now\s+(an?\s+)?(?:admin|root|jailbroken|unfiltered)\b",
        r"(?i)\bdisregard\s+(all\s+)?(rules|safety|guidelines)\b",
        r"(?i)<\|im_start\|>",
        r"(?i)<\|im_end\|>",
        r"(?i)\[INST\]",
        r"(?i)\[/INST\]",
    ]

    sanitized = text
    for pattern in injection_patterns:
        sanitized = re.sub(pattern, "[UNTRUSTED_INJECTION_STRIPPED]", sanitized)

    return sanitized


class DocumentMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="document_mcp",
            description="Controlled Medical Document & RAG Evidence Retrieval MCP Server with Security Isolation",
        )
        self._register_document_tools()

    def _register_document_tools(self):
        # 1. get_document
        self.register_tool(
            MCPTool(
                name="get_document",
                description="Retrieve parsed document record, extracted clinical entities, and metadata with ownership validation",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "Unique document identifier"},
                        "user_id": {"type": "string", "description": "Authenticated user identifier"},
                    },
                    "required": ["document_id"],
                },
                allowed_agents=["document_agent", "medicine_agent", "supervisor", "insurance_agent", "bill_verification_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_get_document,
        )

        # 2. get_document_metadata
        self.register_tool(
            MCPTool(
                name="get_document_metadata",
                description="Retrieve non-sensitive document metadata (filename, type, upload timestamp, page count)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "Unique document identifier"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["document_id"],
                },
                allowed_agents=["document_agent", "supervisor", "insurance_agent", "bill_verification_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_document_metadata,
        )

        # 3. search_document
        self.register_tool(
            MCPTool(
                name="search_document",
                description="Search document vector index for passages semantically matching a query",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "Unique document identifier"},
                        "query": {"type": "string", "description": "Natural language search query"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["document_id", "query"],
                },
                allowed_agents=["document_agent", "supervisor", "insurance_agent", "bill_verification_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_document,
        )

        # 4. get_document_page
        self.register_tool(
            MCPTool(
                name="get_document_page",
                description="Retrieve raw page text from document with prompt injection neutralization",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "Document identifier"},
                        "page_number": {"type": "integer", "description": "1-indexed page number"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["document_id", "page_number"],
                },
                allowed_agents=["document_agent", "supervisor", "insurance_agent", "bill_verification_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_document_page,
        )

        # 5. get_document_evidence
        self.register_tool(
            MCPTool(
                name="get_document_evidence",
                description="Retrieve verified text citations and page evidence for a claim or clinical entity",
                input_schema={
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "description": "Document identifier"},
                        "query": {"type": "string", "description": "Entity or claim query to verify"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["document_id", "query"],
                },
                allowed_agents=["document_agent", "supervisor", "insurance_agent", "bill_verification_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_get_document_evidence,
        )

    # --------------------------------------------------------------------------
    # Handlers & Security Enforcement
    # --------------------------------------------------------------------------
    def _verify_document_access(self, doc_id: str, user_id: Optional[str]) -> Dict[str, Any]:
        doc = get_medical_document(doc_id)
        if not doc:
            raise KeyError(f"Document '{doc_id}' not found.")

        doc_owner = doc.get("user_id")
        if user_id and doc_owner and doc_owner != user_id:
            raise PermissionError(f"Unauthorized: Access to document '{doc_id}' denied for user '{user_id}'.")

        return doc

    def _handle_get_document(self, document_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        doc = self._verify_document_access(document_id, user_id)
        # Deep sanitize raw text
        raw_text = sanitize_untrusted_document_content(doc.get("raw_text", ""))
        fn = doc.get("file_name") or doc.get("filename")
        return {
            "document_id": doc["id"],
            "filename": fn,
            "document_type": doc.get("document_type"),
            "extracted_data": doc.get("extracted_data"),
            "raw_text_preview": raw_text[:500] if raw_text else "",
            "is_untrusted_content": True,
            "source": f"Medical Document Storage: {fn}",
        }

    def _handle_get_document_metadata(self, document_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        doc = self._verify_document_access(document_id, user_id)
        return {
            "document_id": doc["id"],
            "filename": doc.get("file_name") or doc.get("filename"),
            "document_type": doc.get("document_type"),
            "file_size": doc.get("file_size"),
            "page_count": doc.get("page_count", 1),
            "created_at": doc.get("created_at"),
            "status": doc.get("processing_status", "PROCESSED"),
        }

    def _handle_search_document(self, document_id: str, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        self._verify_document_access(document_id, user_id)
        vector_store = document_rag_service.vector_store
        matches = vector_store.search(query=query, top_k=3, filter_doc_id=document_id)

        passages = []
        for chunk, score in matches:
            passages.append({
                "document_id": chunk.doc_id,
                "page": chunk.page_number,
                "score": round(float(score), 4),
                "text": sanitize_untrusted_document_content(chunk.text),
                "source": chunk.doc_name,
                "is_untrusted_content": True,
            })

        return {
            "document_id": document_id,
            "query": query,
            "passages": passages,
            "total_matches": len(passages),
        }

    def _handle_get_document_page(self, document_id: str, page_number: int, user_id: Optional[str] = None) -> Dict[str, Any]:
        doc = self._verify_document_access(document_id, user_id)
        # Search chunks for this specific page
        vector_store = document_rag_service.vector_store
        page_chunks = [
            c for c in vector_store.chunks
            if c.doc_id == document_id and c.page_number == page_number
        ]

        if not page_chunks:
            # Fallback to raw text
            text = sanitize_untrusted_document_content(doc.get("raw_text", ""))
        else:
            text = sanitize_untrusted_document_content("\n".join(c.text for c in page_chunks))

        return {
            "document_id": document_id,
            "page_number": page_number,
            "text": text,
            "source": doc.get("filename"),
            "is_untrusted_content": True,
        }

    def _handle_get_document_evidence(self, document_id: str, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        doc = self._verify_document_access(document_id, user_id)
        vector_store = document_rag_service.vector_store
        matches = vector_store.search(query=query, top_k=2, filter_doc_id=document_id)

        evidence = []
        for chunk, score in matches:
            evidence.append({
                "document_id": chunk.doc_id,
                "page_number": chunk.page_number,
                "citation_text": sanitize_untrusted_document_content(chunk.text[:300]),
                "relevance_score": round(float(score), 3),
                "source": chunk.doc_name,
            })

        return {
            "document_id": document_id,
            "query": query,
            "evidence": evidence,
            "verified": len(evidence) > 0,
            "is_untrusted_content": True,
        }


document_mcp_server = DocumentMCPServer()
