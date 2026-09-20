import re
from app.agents.state import AgentState

SYMPTOM_KEYWORDS = [
    r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bpain\b", r"\bache\b",
    r"\bhurt(s|ing)?\b", r"\bsick\b", r"\bnausea\b", r"\bvomit\b", r"\bdizzy\b",
    r"\bchills\b", r"\btired(ness)?\b", r"\bfatigue\b", r"\bsore\b", r"\brash\b",
    r"\bsymptom(s)?\b", r"\bswollen\b", r"\bcongestion\b", r"\brunny\b",
    r"\btooth\b", r"\bteeth\b", r"\beye(s)?\b", r"\bear(s)?\b",
]

DEPARTMENT_KEYWORDS = [
    r"\bgeneral\s+medicine\b", r"\bdermatolog(y|ist)\b", r"\bent\b",
    r"\borthopedic(s)?\b", r"\bpediatric(s|ian)?\b", r"\bophthalmolog(y|ist)\b",
    r"\bdental\b", r"\bdentist\b", r"\bclinic\b", r"\bdepartment\b",
    r"\bconsultation\b", r"\bdoctor\b", r"\bspecialist\b"
]


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor Agent:
    Evaluates incoming request and decides whether to route to:
    1. 'symptom_agent' (if symptoms are present)
    2. 'department_agent' (if direct department/doctor request without symptoms)
    3. 'final_response' (general conversational message)
    """
    user_msg = state.get("user_message", "").strip().lower()

    has_symptoms = any(re.search(kw, user_msg) for kw in SYMPTOM_KEYWORDS)
    has_dept_query = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

    if has_symptoms:
        route = "symptom_agent"
    elif has_dept_query:
        route = "department_agent"
    else:
        route = "final_response"

    return {
        **state,
        "route": route,
    }


def should_route_from_supervisor(state: AgentState) -> str:
    """Routing choice from supervisor entry point."""
    return state.get("route", "final_response")


def post_symptom_router(state: AgentState) -> str:
    """
    After symptom extraction, route to department_agent if symptoms were found
    or if user indicated an appointment / department preference.
    """
    symptoms = state.get("symptoms", [])
    user_msg = state.get("user_message", "").lower()
    has_dept_query = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

    if symptoms or has_dept_query:
        return "department_agent"
    return "final_response"


def final_response_node(state: AgentState) -> AgentState:
    """
    Final Response:
    Synthesizes conversational reply reflecting extracted symptoms and suggested department.
    """
    symptoms = state.get("symptoms", [])
    dept = state.get("suggested_department")
    user_msg = state.get("user_message", "").strip().lower()

    if symptoms and dept and dept != "Needs clarification":
        formatted = []
        for s in symptoms:
            if s.get("duration"):
                formatted.append(f"{s['name']} ({s['duration']})")
            else:
                formatted.append(s["name"])
        symptoms_str = ", ".join(formatted)

        final_msg = (
            f"I have recorded your symptoms: {symptoms_str}. "
            f"Suggested department: {dept}. "
            "Your healthcare dashboard has been updated. Would you like to select an available doctor or time slot?"
        )
    elif symptoms:
        formatted = [f"{s['name']} ({s['duration']})" if s.get('duration') else s['name'] for s in symptoms]
        final_msg = (
            f"I have recorded your symptoms: {', '.join(formatted)}. "
            "Your healthcare dashboard has been updated."
        )
    elif dept and dept != "Needs clarification":
        final_msg = (
            f"Your request has been routed to the {dept} department. "
            "Your healthcare dashboard has been updated."
        )
    elif any(g in user_msg for g in ["hello", "hi", "hey"]):
        final_msg = "Hello, how can I help you today? Please describe your symptoms or what appointment you need."
    elif dept == "Needs clarification":
        final_msg = "Could you please provide a few more details about your symptoms so I can recommend the right department?"
    else:
        final_msg = "I understand. I can help organize your symptoms and appointment request."

    return {
        **state,
        "final_response": final_msg,
    }
