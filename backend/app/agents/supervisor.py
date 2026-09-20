import re
from app.agents.state import AgentState

# Keywords that indicate the user is describing symptoms or physical complaints
SYMPTOM_KEYWORDS = [
    r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bpain\b", r"\bache\b",
    r"\bhurt(s|ing)?\b", r"\bsick\b", r"\bnausea\b", r"\bvomit\b", r"\bdizzy\b",
    r"\bchills\b", r"\btired(ness)?\b", r"\bfatigue\b", r"\bsore\b", r"\brash\b",
    r"\bsymptom(s)?\b", r"\bswollen\b", r"\bcongestion\b", r"\brunny\b",
]


def supervisor_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Supervisor Agent
    Evaluates the incoming user message and decides routing.
    """
    user_msg = state.get("user_message", "").strip().lower()

    # Determine whether symptom extraction is required
    requires_symptom_extraction = any(
        re.search(kw, user_msg) for kw in SYMPTOM_KEYWORDS
    )

    if requires_symptom_extraction:
        route = "symptom_agent"
    else:
        route = "final_response"

    return {
        **state,
        "route": route,
    }


def should_route(state: AgentState) -> str:
    """Conditional edge routing decision."""
    return state.get("route", "final_response")


def final_response_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Final Response
    Synthesizes the response for the user after agent processing.
    """
    symptoms = state.get("symptoms", [])
    user_msg = state.get("user_message", "").strip().lower()

    if symptoms:
        formatted = []
        for s in symptoms:
            if s.get("duration"):
                formatted.append(f"{s['name']} ({s['duration']})")
            else:
                formatted.append(s["name"])

        symptoms_str = ", ".join(formatted)
        final_msg = (
            f"I have recorded your symptoms: {symptoms_str}. "
            "Your healthcare dashboard has been updated. Would you like me to suggest an appropriate department or doctor?"
        )
    elif any(g in user_msg for g in ["hello", "hi", "hey"]):
        final_msg = "Hello, how can I help you today? You can describe any symptoms you are feeling or request an appointment."
    elif any(a in user_msg for a in ["appointment", "doctor", "slot", "book"]):
        final_msg = "I can help coordinate your appointment. Please share any symptoms you have so I can recommend the right department."
    else:
        final_msg = "I understand. I can help organize your symptoms and appointment request. Please tell me what symptoms you are experiencing."

    return {
        **state,
        "final_response": final_msg,
    }
