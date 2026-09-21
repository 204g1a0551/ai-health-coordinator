import logging
from typing import Dict, Any, List, Optional

from app.models.cost_saver import (
    CostSaverAnalysisResult,
    CostSaverQuestionResponse,
    MedicineComparison,
)
from app.mcp.client import mcp_client
from app.services.cost_saver_service import cost_saver_service
from app.agents.state import AgentState

logger = logging.getLogger(__name__)


class CostSaverAgent:
    """
    Generic Medicine & Cost-Saver Agent.
    Provides informational price comparisons for medicines extracted from prescriptions via medicine_mcp.
    Flow:
    Prescription -> Medicine Extraction -> Normalization -> Cost-Saver Agent
    -> Medicine MCP Server -> Medicine/Price Data Source -> Generic/Equivalent Info -> Price Comparison -> UI Action Agent
    """

    def __init__(self):
        self.service = cost_saver_service

    def get_generic_for_medicine(self, medicine_name: str) -> Dict[str, Any]:
        """Queries Jan Aushadhi / PMBJP generic equivalents via medicine_mcp."""
        mcp_res = mcp_client.call_tool(
            server_name="medicine_mcp",
            tool_name="find_generic_information",
            arguments={"medicine_name": medicine_name},
            caller_agent="cost_saver_agent",
        )
        return mcp_res.data if mcp_res.success and mcp_res.data else {}

    def get_medicine_price_comparison(self, medicine_name: str) -> Dict[str, Any]:
        """Queries side-by-side brand vs generic price comparison via medicine_mcp."""
        mcp_res = mcp_client.call_tool(
            server_name="medicine_mcp",
            tool_name="get_medicine_price",
            arguments={"medicine_name": medicine_name},
            caller_agent="cost_saver_agent",
        )
        return mcp_res.data if mcp_res.success and mcp_res.data else {}

    def analyze_costs(
        self,
        session_id: str = "default",
        document_ids: Optional[List[str]] = None,
        manual_meds: Optional[List[str]] = None,
    ) -> CostSaverAnalysisResult:
        return self.service.analyze_prescriptions_cost(
            session_id=session_id,
            document_ids=document_ids,
            manual_meds=manual_meds,
        )

    def answer_query(self, question: str, session_id: str = "default") -> CostSaverQuestionResponse:
        return self.service.answer_cost_query(question, session_id=session_id)


cost_saver_agent = CostSaverAgent()


def cost_saver_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph Node for Generic Medicine & Cost-Saver Agent.
    Dispatches:
    - SHOW_MEDICINE_COST: List of prescribed medicines with active ingredients and market prices
    - SHOW_GENERIC_OPTIONS: Direct generic/equivalent options with Jan Aushadhi alternatives
    - SHOW_PRICE_COMPARISON: Full side-by-side brand vs. generic price difference matrix
    - SHOW_MEDICINE_SOURCE: Authoritative NPPA / PMBJP price dataset citations and timestamps
    """
    user_msg = state.get("user_message", "").strip().lower()
    parsed = state.get("parsed_intent") or {}
    intent = parsed.get("intent", "")
    session_id = state.get("session_id", "default")

    analysis = cost_saver_service.analyze_prescriptions_cost(session_id=session_id)

    # 1. SHOW_MEDICINE_SOURCE
    if (
        intent in ["SHOW_MEDICINE_SOURCE", "MEDICINE_SOURCE", "PRICE_SOURCE"]
        or "price source" in user_msg
        or "where do prices come from" in user_msg
        or "pricing data source" in user_msg
    ):
        primary_action = "SHOW_MEDICINE_SOURCE"
        primary_data = {
            "analysis": analysis.model_dump(),
            "data_source": analysis.data_source,
            "price_timestamp": analysis.price_timestamp,
            "comparisons": [c.model_dump() for c in analysis.comparisons],
            "session_id": session_id,
        }
        reply = (
            f"**Medicine Pricing Data Source**:\n\n"
            f"• **Source**: {analysis.data_source}\n"
            f"• **Price Timestamp**: {analysis.price_timestamp[:10]}\n"
            f"• **Regulatory Standard**: Drug Price Control Order (DPCO) / Jan Aushadhi Pariyojana\n\n"
            f"All generic prices are verified against authentic government and institutional drug pricing catalogs."
        )

    # 2. SHOW_GENERIC_OPTIONS
    elif (
        intent in ["SHOW_GENERIC_OPTIONS", "GENERIC_OPTIONS", "GENERIC_EQUIVALENT"]
        or "generic options" in user_msg
        or "generic equivalent" in user_msg
        or "generic alternative" in user_msg
        or "cheaper version" in user_msg
    ):
        primary_action = "SHOW_GENERIC_OPTIONS"
        primary_data = {
            "analysis": analysis.model_dump(),
            "comparisons": [c.model_dump() for c in analysis.comparisons],
            "total_potential_savings": analysis.total_potential_savings,
            "session_id": session_id,
        }
        reply = (
            f"**Generic Medicine Equivalents**:\n\n"
            f"I have identified verified generic equivalents for your prescribed medications. "
            f"Potential total savings: **₹{analysis.total_potential_savings}** ({analysis.savings_percentage}%).\n\n"
            f"**Important**: Do not change or substitute the prescribed medicine without consulting your doctor or pharmacist."
        )

    # 3. SHOW_MEDICINE_COST
    elif (
        intent in ["SHOW_MEDICINE_COST", "MEDICINE_COST", "PRESCRIPTION_COST"]
        or "medicine cost" in user_msg
        or "how much do these cost" in user_msg
        or "cost of prescription" in user_msg
        or "current listed price" in user_msg
    ):
        primary_action = "SHOW_MEDICINE_COST"
        primary_data = {
            "analysis": analysis.model_dump(),
            "comparisons": [c.model_dump() for c in analysis.comparisons],
            "total_prescribed_cost": analysis.total_prescribed_cost,
            "session_id": session_id,
        }
        reply = (
            f"**Prescribed Medicine Cost Analysis**:\n\n"
            f"Estimated total cost of prescribed branded medicines: **₹{analysis.total_prescribed_cost}**.\n"
            f"You can view the per-medicine breakdown on the left canvas."
        )

    # 4. SHOW_PRICE_COMPARISON (Default)
    else:
        primary_action = "SHOW_PRICE_COMPARISON"
        primary_data = {
            "analysis": analysis.model_dump(),
            "comparisons": [c.model_dump() for c in analysis.comparisons],
            "total_prescribed_cost": analysis.total_prescribed_cost,
            "potential_generic_cost": analysis.potential_generic_cost,
            "total_potential_savings": analysis.total_potential_savings,
            "savings_percentage": analysis.savings_percentage,
            "session_id": session_id,
        }
        reply = (
            f"**Medicine Cost-Saver & Price Comparison**\n\n"
            f"• **Prescribed Branded Cost**: ₹{analysis.total_prescribed_cost}\n"
            f"• **Potential Generic Cost**: ₹{analysis.potential_generic_cost}\n"
            f"• **Potential Savings**: **₹{analysis.total_potential_savings}** ({analysis.savings_percentage}%)\n\n"
            f"Detailed comparison matrix with active ingredients and bioequivalence notes has been loaded on the left.\n\n"
            f"**Important Notice**: Do not change or substitute the prescribed medicine without consulting your doctor or pharmacist."
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
