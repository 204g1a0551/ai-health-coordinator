from typing import Any, Dict

from app.agents.state import AgentState
from app.services.timeline_service import timeline_service


def timeline_agent_node(state: AgentState) -> AgentState:
    intent = (state.get("parsed_intent") or {}).get("intent", "")
    session_id = state.get("session_id", "default")
    if intent == "MEDICAL_EXPENSES":
        data = timeline_service.get_expenses(session_id).dict()
        action = "SHOW_MEDICAL_EXPENSES"
        reply = f"Your recorded medical expenses total {data['total']:.2f}."
    elif intent == "DOCUMENT_HISTORY":
        events = timeline_service.get_timeline(session_id)
        data = {"documents": [event.dict() for event in events]}
        action = "SHOW_DOCUMENT_HISTORY"
        reply = f"I found {len(events)} uploaded medical document(s) in your history."
    else:
        events = timeline_service.get_timeline(session_id)
        data = {"events": [event.dict() for event in events]}
        action = "SHOW_MEDICAL_TIMELINE"
        reply = f"I found {len(events)} medical timeline event(s)."
    return {
        **state,
        "primary_ui_action": action,
        "primary_ui_data": data,
        "final_response": reply,
    }
