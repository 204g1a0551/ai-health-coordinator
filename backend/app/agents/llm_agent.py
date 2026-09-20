from typing import Dict, Any
from app.agents.state import AgentState
from app.services.llm_service import llm_service


def llm_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: LLM Intent & Entity Extraction Layer
    Executes first in the pipeline.
    Uses LLM / contextual NLU to extract structured intents and entities from natural language.
    Does NOT access or modify database tables directly.
    """
    user_msg = state.get("user_message", "").strip()
    session_id = state.get("session_id", "default-session")

    parsed = llm_service.parse_intent_and_entities(user_msg, session_id)
    parsed_dict = parsed.dict()

    symptoms = state.get("symptoms", [])
    if parsed.symptoms:
        symptoms = [{"name": s.name, "duration": s.duration} for s in parsed.symptoms]

    suggested_dept = parsed.department or state.get("suggested_department")
    location_query = parsed.location or state.get("location_query")

    return {
        **state,
        "parsed_intent": parsed_dict,
        "symptoms": symptoms,
        "suggested_department": suggested_dept,
        "location_query": location_query,
        "clarification_question": parsed.clarification_question,
    }
