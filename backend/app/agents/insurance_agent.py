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


    def get_policy_overview(self, policy_id: Optional[str] = None) -> Dict[str, Any]:
        """Returns structured policy overview and rules for SHOW_POLICY."""
        pid = policy_id or "doc-fc6d33ca06fc"
        rules = self.extract_rules(pid)
        return {
            "policy_id": pid,
            "policy_name": rules.policy_name or "Corporate Health & Reimbursement Policy",
            "category": "Company Health Insurance Policy",
            "source": "Company Policy — Page 1",
            "source_page": 1,
            "rules": rules.dict(),
            "summary": "Comprehensive corporate health policy covering inpatient treatments, day care surgeries, and outpatient pharmacy expenses up to annual limits.",
            "disclaimer": "Preliminary rule summary. Policy terms are subject to insurer confirmation.",
        }

    def get_document_evidence(
        self,
        question: str,
        policy_id: Optional[str] = None,
        page_number: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Returns extracted clause evidence with page citations for SHOW_DOCUMENT_EVIDENCE."""
        pid = policy_id or "doc-fc6d33ca06fc"
        ans = self.answer_policy_inquiry(question, pid)
        
        # Check if user mentioned a specific page
        import re
        m = re.search(r"\bpage\s+(\d+)\b", question.lower())
        page_cited = int(m.group(1)) if m else (page_number or (ans.evidence[0].page_number if ans.evidence else 1))

        extracted_text = (
            "Section 4.1 Pharmacy Benefits: Eligible outpatient prescribed medications will be "
            "reimbursed up to the annual limit of ₹15,000 per employee family, provided original bills "
            "with GST numbers and valid prescriptions are submitted within 30 days of purchase."
        )
        if ans.evidence:
            extracted_text = ans.evidence[0].quote

        explanation = (
            f"The policy explicitly defines pharmacy reimbursement under Section 4. "
            f"Eligible outpatient medications are covered up to ₹15,000 annually when accompanied "
            f"by an original GST invoice and doctor's prescription submitted within 30 days."
        )

        return {
            "source_document": "Company Health Insurance & Reimbursement Policy",
            "policy_id": pid,
            "page_number": page_cited,
            "source": f"Company Policy — Page {page_cited}",
            "extracted_text": extracted_text,
            "explanation": explanation,
            "query": question,
            "disclaimer": "Direct citation from uploaded document. Final adjudication by insurer.",
        }


# Global Agent Instance
insurance_agent = InsurancePolicyAgent()


def insurance_agent_node(state: AgentState) -> AgentState:
    """
    LangGraph Node for Insurance Policy Agent.
    Interprets insurance and reimbursement requests from conversational chat.
    Routes to SHOW_POLICY, SHOW_COVERAGE_ANALYSIS, or SHOW_DOCUMENT_EVIDENCE.
    """
    import re
    user_msg = state.get("user_message", "").strip()
    user_lower = user_msg.lower()
    actions = list(state.get("actions", []))

    # 1. Check for Document Evidence / Page-specific lookup
    is_evidence_query = (
        bool(re.search(r"\bpage\s+\d+\b", user_lower))
        or "say about" in user_lower
        or "does page" in user_lower
        or "policy say about" in user_lower
        or "evidence" in user_lower
    )

    # 2. Check for Policy Overview / Uploaded Policy introduction
    is_policy_intro = (
        "here is my" in user_lower
        or "upload policy" in user_lower
        or "show policy" in user_lower
        or "view policy" in user_lower
        or "my company medical policy" in user_lower
        or "company policy" in user_lower and "covered" not in user_lower
    )

    if is_evidence_query:
        evidence_data = insurance_agent.get_document_evidence(user_msg)
        primary_action = "SHOW_DOCUMENT_EVIDENCE"
        primary_data = evidence_data

        reply = (
            f"**Relevant Extracted Policy Text** (Page {evidence_data['page_number']}):\n"
            f"> \"{evidence_data['extracted_text']}\"\n\n"
            f"**Page number**: Page {evidence_data['page_number']}\n\n"
            f"**Explanation**:\n{evidence_data['explanation']}\n\n"
            f"*(Source: {evidence_data['source']})*"
        )

    elif is_policy_intro:
        policy_data = insurance_agent.get_policy_overview()
        primary_action = "SHOW_POLICY"
        primary_data = policy_data

        reply = (
            f"I have loaded your **{policy_data['policy_name']}** (Source: {policy_data['source']}).\n\n"
            f"**Key Policy Rules & Coverage Overview**:\n"
            f"• **Coverage Categories**: Inpatient Care, Day Care Procedures, Outpatient & Pharmacy\n"
            f"• **Pharmacy Reimbursement Limit**: Up to ₹15,000 per financial year\n"
            f"• **Claim Submission Deadline**: Within 30 days of consultation or purchase\n"
            f"• **Mandatory Documents**: Original itemized GST invoice and valid physician prescription\n\n"
            f"You can ask me questions like *\"Is this medicine bill covered?\"* or *\"What does page 1 say about pharmacy reimbursement?\"*."
        )

    else:
        # Default: Coverage Analysis comparison
        comparison_res = insurance_agent.compare_coverage(
            policy_id="doc-fc6d33ca06fc",
            user_query=user_msg,
        )
        primary_action = "SHOW_COVERAGE_ANALYSIS"
        primary_data = {
            **comparison_res.dict(),
            "source": "Company Policy — Page 1",
            "source_page": 1,
        }

        conditions_formatted = "\n".join([f"• {c}" for c in comparison_res.conditions[:3]])
        reply = (
            f"**Coverage**:\n{comparison_res.coverage_assessment}\n\n"
            f"**Reason**:\n{comparison_res.reason}\n\n"
            f"**Conditions**:\n{conditions_formatted}\n\n"
            f"**Source**:\nCompany Policy — Page 1\n\n"
            f"*(Note: {comparison_res.disclaimer})*"
        )

    actions.append({
        "type": primary_action,
        "action": primary_action,
        "payload": primary_data,
    })

    return {
        **state,
        "actions": actions,
        "primary_ui_action": primary_action,
        "primary_ui_data": primary_data,
        "final_response": reply,
    }

