import logging
from typing import Dict, Any, List, Optional

from app.models.insurance import (
    ExtractedPolicyRules,
    CoverageComparisonResponse,
    PolicyAnswerResponse,
    PolicyUploadCategory,
)
from app.services.insurance_rag_service import insurance_rag_service
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class InsurancePolicyAgent:
    """
    Autonomous Insurance Policy & Reimbursement Agent.
    Implements 9 core clinical and insurance adjudication analysis responsibilities:
    1. Extract policy rules.
    2. Identify coverage categories.
    3. Identify exclusions.
    4. Identify reimbursement limits.
    5. Identify pharmacy/medicine rules.
    6. Identify outpatient/inpatient rules.
    7. Identify required documents.
    8. Identify claim submission deadlines.
    9. Compare the policy against the user's uploaded prescription or bill.
    """

    def __init__(self):
        self.rag_service = insurance_rag_service

    def extract_rules(self, policy_id: str) -> ExtractedPolicyRules:
        """Responsibilities 1-8: Extract multi-dimensional insurance rules."""
        return self.rag_service.extract_policy_rules(policy_id)

    def compare_coverage(
        self,
        policy_id: str,
        medical_document_id: Optional[str] = None,
        user_query: Optional[str] = None,
    ) -> CoverageComparisonResponse:
        """Responsibility 9: Compare policy against user's uploaded prescription or bill."""
        return self.rag_service.compare_documents(
            policy_id=policy_id,
            medical_doc_id=medical_document_id,
            user_query=user_query,
        )

    def answer_policy_inquiry(
        self,
        question: str,
        policy_id: Optional[str] = None,
    ) -> PolicyAnswerResponse:
        """Interactive RAG inquiry answer regarding policy rules and limits."""
        return self.rag_service.answer_policy_query(
            question=question,
            policy_id=policy_id,
        )


# Global Agent Instance
insurance_agent = InsurancePolicyAgent()


def insurance_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph Node for Insurance Policy Agent.
    Interprets insurance and reimbursement requests from conversational chat.
    """
    user_msg = state.get("user_message", "").strip()
    actions = list(state.get("actions", []))

    # Evaluate query using Insurance RAG pipeline
    answer_res = insurance_agent.answer_policy_inquiry(user_msg)

    # Format structured action for the dynamic canvas
    comparison_res = insurance_agent.compare_coverage(
        policy_id="doc-fc6d33ca06fc",  # default corporate reimbursement policy
        user_query=user_msg,
    )

    actions.append({
        "type": "SHOW_INSURANCE_COVERAGE",
        "action": "SHOW_INSURANCE_COVERAGE",
        "payload": comparison_res.dict(),
    })

    reply = (
        f"**Coverage Assessment**: {comparison_res.coverage_assessment}\n\n"
        f"{comparison_res.reason}\n\n"
        f"**Required Conditions**:\n"
        + "\n".join([f"• {c}" for c in comparison_res.conditions[:3]])
        + f"\n\n*(Note: {comparison_res.disclaimer})*"
    )

    return {
        **state,
        "actions": actions,
        "primary_ui_action": "SHOW_INSURANCE_COVERAGE",
        "primary_ui_data": comparison_res.dict(),
        "final_response": reply,
    }
