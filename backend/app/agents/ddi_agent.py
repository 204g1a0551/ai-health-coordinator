import logging
import re
from typing import Dict, Any, List, Optional

from app.models.drug_interaction import (
    DDIAnalysisResult,
    DDIQuestionResponse,
    DrugInteractionPair,
)
from app.services.ddi_service import ddi_service
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class DDICheckerAgent:
    """
    Drug-Drug Interaction (DDI) Checker Agent.
    Analyzes medicines extracted across multiple prescriptions and documents.
    Flow:
    Prescriptions -> Document Agent -> Medicine Extraction -> Medicine Normalization
    -> DDI Checker Agent -> Drug Interaction Database -> Interaction Results -> UI Action Agent
    """

    def __init__(self):
        self.service = ddi_service

    def analyze_interactions(
        self,
        session_id: str = "default",
        document_ids: Optional[List[str]] = None,
        manual_meds: Optional[List[str]] = None,
    ) -> DDIAnalysisResult:
        return self.service.analyze_cross_prescription_interactions(
            session_id=session_id,
            document_ids=document_ids,
            manual_meds=manual_meds,
        )

    def answer_query(self, question: str, session_id: str = "default") -> DDIQuestionResponse:
        return self.service.answer_interaction_query(question, session_id=session_id)


ddi_checker_agent = DDICheckerAgent()


def ddi_checker_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph Node for Drug-Drug Interaction Checker.
    Dispatches:
    - SHOW_DRUG_INTERACTIONS: Overview of potential interactions, severity badges, and warnings
    - SHOW_INTERACTION_DETAILS: Deep clinical mechanisms and authoritative citations
    - SHOW_MEDICATION_LIST: Consolidated multi-prescription normalized active medication inventory
    """
    user_msg = state.get("user_message", "").strip().lower()
    parsed = state.get("parsed_intent") or {}
    intent = parsed.get("intent", "")
    session_id = state.get("session_id", "default")

    analysis = ddi_service.analyze_cross_prescription_interactions(session_id=session_id)

    # 1. SHOW_INTERACTION_DETAILS
    if (
        intent in ["INTERACTION_DETAILS", "SHOW_INTERACTION_DETAILS"]
        or "interaction details" in user_msg
        or "how do they interact" in user_msg
        or "interaction mechanism" in user_msg
    ):
        primary_action = "SHOW_INTERACTION_DETAILS"
        primary_data = {
            "analysis": analysis.model_dump(),
            "interactions": [i.model_dump() for i in analysis.interactions],
            "unverified_pairs": [u.model_dump() for u in analysis.unverified_pairs],
            "total_medications": analysis.total_medications,
            "session_id": session_id,
        }
        reply = (
            f"**Drug Interaction Clinical Details**:\n\n"
            f"I have reviewed the pharmacological mechanisms for your {len(analysis.interactions)} identified interaction(s). "
            f"Please refer to the clinical details card on the left.\n\n"
            f"**Clinical Reminder**: Do not stop or alter any medication without discussing with your doctor."
        )

    # 2. SHOW_MEDICATION_LIST
    elif (
        intent in ["SHOW_MEDICATION_LIST", "MEDICATION_LIST", "CONSOLIDATED_MEDICINES"]
        or "medication list" in user_msg
        or "all my medicines" in user_msg
        or "active medications" in user_msg
        or "medicines from all prescriptions" in user_msg
    ):
        primary_action = "SHOW_MEDICATION_LIST"
        primary_data = {
            "analysis": analysis.model_dump(),
            "medications": [m.model_dump() for m in analysis.medications],
            "duplicates": analysis.duplicate_medications,
            "session_id": session_id,
        }
        reply = (
            f"**Consolidated Medication List**:\n\n"
            f"Here is the normalized list of **{analysis.total_medications} active medication(s)** extracted across your uploaded prescriptions. "
            f"Details and potential duplicate warnings are shown in the canvas on the left."
        )

    # 3. SHOW_DRUG_INTERACTIONS (Default DDI Action)
    else:
        primary_action = "SHOW_DRUG_INTERACTIONS"
        primary_data = {
            "analysis": analysis.model_dump(),
            "interactions": [i.model_dump() for i in analysis.interactions],
            "duplicates": analysis.duplicate_medications,
            "total_medications": analysis.total_medications,
            "interactions_found": analysis.interactions_found,
            "session_id": session_id,
        }

        if analysis.interactions:
            top_interaction = analysis.interactions[0]
            reply = (
                f"**Potential Drug-Drug Interaction Detected**\n\n"
                f"⚠️ **{top_interaction.medicine_a.normalized_name.title()} + {top_interaction.medicine_b.normalized_name.title()}** "
                f"({top_interaction.severity.value} Severity)\n\n"
                f"The authoritative database (*{top_interaction.source}*) reports: {top_interaction.description}\n\n"
                f"**Clinical Guidance**:\n"
                f"• {top_interaction.warning}\n"
                f"• Please consult your doctor or pharmacist before changing, stopping, or combining medicines.\n"
                f"• Do not alter your prescribed dosages without medical consultation."
            )
        else:
            reply = (
                f"**Drug Interaction Analysis**:\n\n"
                f"Analyzed {analysis.total_medications} medication(s) across your documents. "
                f"Interaction information could not be verified from the configured source for any acute interaction. "
                f"Please note: This does not guarantee that no interaction exists. Always consult your doctor or pharmacist."
            )

    action_payload = {
        "action": primary_action,
        "type": primary_action,
        "payload": primary_data,
        "data": primary_data,
    }

    return {
        **state,
        "primary_ui_action": primary_action,
        "primary_ui_data": primary_data,
        "actions": [action_payload],
        "final_response": reply,
    }
