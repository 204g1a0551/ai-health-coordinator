import re
from app.agents.state import AgentState

SYMPTOM_KEYWORDS = [
    r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bpain\b", r"\bache\b",
    r"\bhurt(s|ing)?\b", r"\bsick\b", r"\bnausea\b", r"\bvomit\b", r"\bdizzy\b",
    r"\bchills\b", r"\btired(ness)?\b", r"\bfatigue\b", r"\bsore\b", r"\brash\b",
    r"\bsymptom(s)?\b", r"\bswollen\b", r"\bcongestion\b", r"\brunny\b",
    r"\btooth\b", r"\bteeth\b", r"\beye(s)?\b", r"\bear(s)?\b",
]

BOOKING_KEYWORDS = [
    r"\bbook\b", r"\bappointment\b", r"\bslot(s)?\b", r"\bdoctor(s)?\b",
    r"\bphysician\b", r"\bschedule\b", r"\btomorrow\b", r"\bevening\b",
    r"\bmorning\b", r"\bafternoon\b", r"\bvisit\b", r"\bconsult\b"
]

DEPARTMENT_KEYWORDS = [
    r"\bgeneral\s+medicine\b", r"\bdermatolog(y|ist)\b", r"\bent\b",
    r"\borthopedic(s)?\b", r"\bpediatric(s|ian)?\b", r"\bophthalmolog(y|ist)\b",
    r"\bdental\b", r"\bdentist\b", r"\bclinic\b", r"\bdepartment\b",
    r"\bgeneral\s+physician\b"
]


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor Agent:
    Evaluates the user's intent and determines initial agent routing:
    - 'symptom_agent' if symptoms are detected
    - 'doctor_slot_agent' if user specifically requests booking, doctors, or slots
    - 'department_agent' if direct department inquiry
    - 'final_response' if general conversational greeting
    """
    user_msg = state.get("user_message", "").strip().lower()

    has_symptoms = any(re.search(kw, user_msg) for kw in SYMPTOM_KEYWORDS)
    has_booking = any(re.search(kw, user_msg) for kw in BOOKING_KEYWORDS)
    has_dept = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

    if has_symptoms:
        route = "symptom_agent"
    elif has_booking:
        route = "doctor_slot_agent"
    elif has_dept:
        route = "department_agent"
    else:
        route = "final_response"

    return {
        **state,
        "route": route,
    }


def should_route_from_supervisor(state: AgentState) -> str:
    """Entry routing decision from supervisor."""
    return state.get("route", "final_response")


def post_symptom_router(state: AgentState) -> str:
    """
    After symptom extraction, route to department_agent if symptoms or department queries exist.
    """
    symptoms = state.get("symptoms", [])
    user_msg = state.get("user_message", "").lower()
    has_dept_query = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

    if symptoms or has_dept_query:
        return "department_agent"
    return "final_response"


def post_department_router(state: AgentState) -> str:
    """
    After department suggestion, route to doctor_slot_agent to find available doctors and slots
    for that department.
    """
    dept = state.get("suggested_department")
    if dept and dept != "Needs clarification":
        return "doctor_slot_agent"
    return "final_response"


def final_response_node(state: AgentState) -> AgentState:
    """
    Final Response:
    Synthesizes the overall response summarizing symptoms, department, and doctor/slot options.
    """
    symptoms = state.get("symptoms", [])
    dept = state.get("suggested_department")
    doc_results = state.get("doctor_slot_results")
    user_msg = state.get("user_message", "").strip().lower()

    # If doctor/slot results were obtained
    if doc_results and doc_results.get("doctors"):
        doctors = doc_results["doctors"]
        target_dept = doc_results.get("department", dept or "the requested department")

        doc_summaries = []
        for d in doctors:
            slots_str = ", ".join(d["slots"]) if d["slots"] else "No open slots"
            doc_summaries.append(f"{d['name']} ({slots_str})")

        doctors_text = "; ".join(doc_summaries)

        if symptoms:
            sym_text = ", ".join([f"{s['name']}" for s in symptoms])
            final_msg = (
                f"I noted your symptoms ({sym_text}) and routed your request to {target_dept}. "
                f"Available doctors: {doctors_text}. "
                "The doctors and slots have been updated on your dashboard. Please select your preferred slot."
            )
        else:
            final_msg = (
                f"Available doctors in {target_dept}: {doctors_text}. "
                "Your dashboard has been updated with these options. Please select a slot to proceed."
            )
        return {
            **state,
            "final_response": final_msg,
        }

    # If department was suggested
    if dept and dept != "Needs clarification":
        if symptoms:
            sym_text = ", ".join([f"{s['name']}" for s in symptoms])
            final_msg = (
                f"I have recorded your symptoms: {sym_text}. "
                f"Suggested department: {dept}. "
                "Your dashboard has been updated. Please let me know your preferred date and time to see available slots."
            )
        else:
            final_msg = f"Your request has been routed to {dept}. Please let me know if you would like to book a slot."
        return {
            **state,
            "final_response": final_msg,
        }

    if any(g in user_msg for g in ["hello", "hi", "hey"]):
        final_msg = "Hello, how can I help you today? You can describe any symptoms you are experiencing or request an appointment."
    else:
        final_msg = "I understand. I can help organize your symptoms and appointment request. Please tell me your symptoms or preferred doctor."

    return {
        **state,
        "final_response": final_msg,
    }
