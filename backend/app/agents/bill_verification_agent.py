import logging
import re
from typing import Dict, Any, List, Optional

from app.models.bill_verification import (
    BillVerificationData,
    VerificationEvidenceData,
    VerificationQuestionResponse,
)
from app.services.bill_verification_service import bill_verification_service
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class BillVerificationAgent:
    """
    Bill Verification Agent.
    Orchestrates comparison between doctor prescriptions and pharmacy invoices:
    - Flow: Prescription -> Medicine Extraction, Bill -> Bill Extraction
    - Both -> Comparison -> UI Action Agent
    - Strict guardrails: No medical appropriateness judgment, no substitution recommendation.
    """

    def __init__(self):
        self.service = bill_verification_service

    def get_comparison(
        self,
        prescription_id: Optional[str] = None,
        bill_id: Optional[str] = None,
    ) -> BillVerificationData:
        res = self.service.verify_documents(prescription_id, bill_id)
        try:
            from app.security.audit_trail import audit_trail, AuditAction
            audit_trail.record_event(
                action=AuditAction.BILL_ANALYZED,
                user_id="patient_session",
                resource_type="FINANCIAL_DOCUMENT",
                resource_id=bill_id or "default_bill",
                purpose="INSURANCE_ANALYSIS",
                details=f"document_id={bill_id or 'default_bill'} agent=BILL_VERIFICATION_AGENT discrepancies_count={res.discrepancy_count}"
            )
        except Exception:
            pass
        return res

    def get_evidence(
        self,
        prescription_id: Optional[str] = None,
        bill_id: Optional[str] = None,
    ) -> VerificationEvidenceData:
        return self.service.get_verification_evidence(prescription_id, bill_id)

    def answer_query(
        self,
        question: str,
        prescription_id: Optional[str] = None,
        bill_id: Optional[str] = None,
    ) -> VerificationQuestionResponse:
        return self.service.answer_verification_query(question, prescription_id, bill_id)


bill_verification_agent = BillVerificationAgent()


def bill_verification_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph Node for Prescription & Bill Verification:
    - SHOW_BILL_COMPARISON: Complete textual comparison matrix (Medicine | Rx | Bill | Difference)
    - SHOW_BILL_DETAILS: Pharmacy invoice breakdown, tax, and total pricing
    - SHOW_VERIFICATION_EVIDENCE: Side-by-side extracted raw document excerpts
    """
    user_msg = state.get("user_message") or ""
    if not user_msg:
        messages = state.get("messages", [])
        user_msg = messages[-1].get("content", "") if messages else ""
    user_lower = user_msg.lower().strip()
    actions = list(state.get("actions", []))

    is_evidence = any(k in user_lower for k in [
        "verification evidence", "bill evidence", "show evidence", "extracted text", "raw text"
    ])
    is_details = any(k in user_lower for k in [
        "bill details", "show bill details", "invoice details", "pharmacy bill details",
        "tax breakdown", "bill amount", "total bill"
    ])

    if is_evidence:
        evidence = bill_verification_agent.get_evidence()
        primary_action = "SHOW_VERIFICATION_EVIDENCE"
        primary_data = evidence.dict()

        discrepancies_formatted = "\n".join([f"• {d}" for d in evidence.detected_discrepancies])
        reply = (
            f"### Prescription & Bill Verification Evidence\n\n"
            f"**Prescription Source**: `{evidence.prescription_source}`\n"
            f"> \"{evidence.prescription_text}\"\n\n"
            f"**Pharmacy Bill Source**: `{evidence.bill_source}`\n"
            f"> \"{evidence.bill_text}\"\n\n"
            f"**Detected Discrepancies**:\n{discrepancies_formatted}\n\n"
            f"*(Note: {evidence.disclaimer})*"
        )

    elif is_details:
        data = bill_verification_agent.get_comparison()
        fin = data.financial_summary
        primary_action = "SHOW_BILL_DETAILS"
        primary_data = {
            "prescription_file": data.prescription_file,
            "bill_file": data.bill_file,
            "financial_summary": fin.dict(),
            "items": [c.dict() for c in data.comparisons if c.difference_type != "MISSING_FROM_BILL"],
            "disclaimer": data.disclaimer,
        }

        reply = (
            f"### Pharmacy Invoice Details: {fin.invoice_no}\n\n"
            f"• **Pharmacy**: {fin.pharmacy_name}\n"
            f"• **GSTIN**: {fin.gstin}\n"
            f"• **Date**: {fin.bill_date}\n"
            f"• **Subtotal**: ₹{fin.subtotal:.2f}\n"
            f"• **GST (12%)**: ₹{fin.gst_tax:.2f}\n"
            f"• **Total Amount Paid**: **₹{fin.total_amount:.2f}** via {fin.payment_mode}\n\n"
            f"*(Source: {data.bill_file}, Page 1)*"
        )

    else:
        # Default: SHOW_BILL_COMPARISON
        data = bill_verification_agent.get_comparison()
        primary_action = "SHOW_BILL_COMPARISON"
        primary_data = data.dict()

        table_rows = []
        for c in data.comparisons:
            badge = "✓ Match" if not c.is_discrepancy else f"⚠️ {c.difference_type.replace('_', ' ').title()}"
            table_rows.append(f"• **{c.medicine_name}**: {badge} — {c.difference_description}")

        reply = (
            f"### Prescription & Bill Verification Comparison\n\n"
            f"**Prescription**: `{data.prescription_file}` | **Pharmacy Bill**: `{data.bill_file}`\n\n"
            f"• **Total Prescribed**: {data.total_prescribed} item(s)\n"
            f"• **Total Billed**: {data.total_billed} item(s)\n"
            f"• **Matches**: {data.matched_count} | **Discrepancies**: {data.discrepancy_count}\n\n"
            + "\n".join(table_rows)
            + f"\n\n**Total Bill Amount**: **₹{data.financial_summary.total_amount:.2f}**\n\n"
            f"*(Note: {data.disclaimer})*"
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
