"""
Insurance Policy MCP Server
Controlled policy RAG search, coverage clause lookup, and claim document checklists.
Strict informational boundary: never guarantees claim approval or rejection.
"""

from typing import Any, Dict, List, Optional
from app.mcp.base_server import BaseMCPServer
from app.mcp.models import MCPTool
from app.services.insurance_rag_service import insurance_rag_service, DISCLAIMER_TEXT
from app.db.repository import get_medical_document


class InsuranceMCPServer(BaseMCPServer):
    def __init__(self):
        super().__init__(
            name="insurance_mcp",
            description="Health Insurance Policy Clause & Claim Requirement Retrieval MCP Server",
        )
        self._register_insurance_tools()

    def _register_insurance_tools(self):
        # 1. search_policy
        self.register_tool(
            MCPTool(
                name="search_policy",
                description="Search insurance policy clauses and terms matching a specific inquiry (e.g. OPD, medicines)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Insurance inquiry or term"},
                        "policy_id": {"type": "string", "description": "Optional policy document ID"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["query"],
                },
                allowed_agents=["insurance_agent", "supervisor", "document_agent"],
                cache_ttl_seconds=300,
            ),
            self._handle_search_policy,
        )

        # 2. get_policy_clause
        self.register_tool(
            MCPTool(
                name="get_policy_clause",
                description="Retrieve a specific clause (e.g. Pharmacy Coverage, Pre-existing conditions, OPD limits)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "clause_name": {"type": "string", "description": "Name of clause or category"},
                        "policy_id": {"type": "string", "description": "Optional policy document ID"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["clause_name"],
                },
                allowed_agents=["insurance_agent", "supervisor", "document_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_policy_clause,
        )

        # 3. get_policy_page
        self.register_tool(
            MCPTool(
                name="get_policy_page",
                description="Retrieve raw policy content for a specific page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "policy_id": {"type": "string", "description": "Policy document identifier"},
                        "page_number": {"type": "integer", "description": "Page number (1-indexed)"},
                        "user_id": {"type": "string", "description": "User identifier"},
                    },
                    "required": ["policy_id", "page_number"],
                },
                allowed_agents=["insurance_agent", "supervisor", "document_agent"],
                cache_ttl_seconds=600,
            ),
            self._handle_get_policy_page,
        )

        # 4. get_required_claim_documents
        self.register_tool(
            MCPTool(
                name="get_required_claim_documents",
                description="Retrieve mandatory checklist of documentation needed for insurance claim submission",
                input_schema={
                    "type": "object",
                    "properties": {
                        "claim_type": {"type": "string", "description": "Claim category: pharmacy, opd, hospitalization, lab"},
                    },
                    "required": ["claim_type"],
                },
                allowed_agents=["insurance_agent", "supervisor", "bill_verification_agent"],
                cache_ttl_seconds=3600,
            ),
            self._handle_get_required_claim_documents,
        )

    # --------------------------------------------------------------------------
    # Handlers
    # --------------------------------------------------------------------------
    def _handle_search_policy(
        self,
        query: str,
        policy_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if policy_id and user_id:
            doc = get_medical_document(policy_id)
            if doc and doc.get("user_id") and doc["user_id"] != user_id:
                raise PermissionError(f"Unauthorized: Access to policy '{policy_id}' denied.")

        ans = insurance_rag_service.answer_policy_query(query=query, policy_id=policy_id)
        return {
            "query": query,
            "answer": ans.answer,
            "evidence": [e.dict() for e in ans.evidence],
            "potentially_covered": ans.coverage_category.value if ans.coverage_category else "UNCERTAIN",
            "disclaimer": DISCLAIMER_TEXT,
            "source": ans.policy_name,
        }

    def _handle_get_policy_clause(
        self,
        clause_name: str,
        policy_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        ans = insurance_rag_service.answer_policy_query(query=clause_name, policy_id=policy_id)
        return {
            "clause_name": clause_name,
            "summary": ans.answer,
            "evidence": [e.dict() for e in ans.evidence],
            "disclaimer": DISCLAIMER_TEXT,
            "source": ans.policy_name,
        }

    def _handle_get_policy_page(
        self,
        policy_id: str,
        page_number: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if user_id:
            doc = get_medical_document(policy_id)
            if doc and doc.get("user_id") and doc["user_id"] != user_id:
                raise PermissionError(f"Unauthorized: Access to policy '{policy_id}' denied.")

        vector_store = insurance_rag_service.vector_store
        page_chunks = [
            c for c in vector_store.chunks
            if c.policy_id == policy_id and c.page_number == page_number
        ]
        text = "\n".join(c.text for c in page_chunks) if page_chunks else "Page content not found."

        return {
            "policy_id": policy_id,
            "page_number": page_number,
            "text": text,
            "disclaimer": DISCLAIMER_TEXT,
        }

    def _handle_get_required_claim_documents(self, claim_type: str) -> Dict[str, Any]:
        c_type = claim_type.lower()
        if "pharm" in c_type or "med" in c_type:
            docs = [
                {"document": "Itemized Pharmacy Bill / Cash Receipt", "mandatory": True, "notes": "Must list patient name, date, medicine name, batch number, and GSTIN"},
                {"document": "Doctor Prescription", "mandatory": True, "notes": "Must match medicines and consultation date on bill"},
                {"document": "Doctor Consultation Notes", "mandatory": False, "notes": "Recommended for high-value claims"},
                {"document": "Cancelled Cheque / Bank Details", "mandatory": True, "notes": "For direct bank reimbursement transfer"},
            ]
        elif "hosp" in c_type or "inpatient" in c_type:
            docs = [
                {"document": "Discharge Summary / Card", "mandatory": True, "notes": "Detailed treatment history signed by attending physician"},
                {"document": "Itemized Final Hospital Bill", "mandatory": True, "notes": "Breakup of room rent, nursing, medicines, and investigations"},
                {"document": "Payment Receipts", "mandatory": True, "notes": "Stamped and signed payment receipts"},
                {"document": "Investigation / Diagnostic Reports", "mandatory": True, "notes": "Lab and radiology reports supporting admission"},
            ]
        else:
            docs = [
                {"document": "Doctor Consultation Bill & Prescription", "mandatory": True, "notes": "Signed and stamped by consulting physician"},
                {"document": "Payment Proof", "mandatory": True, "notes": "Digital payment confirmation or cash receipt"},
                {"document": "Policy Card / Claim Form", "mandatory": True, "notes": "Signed reimbursement claim form Part A & B"},
            ]

        return {
            "claim_type": claim_type,
            "required_documents": docs,
            "disclaimer": DISCLAIMER_TEXT,
            "source": "Standard Health Insurance Claim Adjudication Guidelines",
        }


insurance_mcp_server = InsuranceMCPServer()
