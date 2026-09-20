import re
from app.agents.state import AgentState

# Specific booking action patterns (booking specific doctor/time)
BOOKING_ACTION_PATTERNS = [
    r"\bbook\s+(?:dr\.?|doctor)\b",
    r"\bbook\s+dr\b",
    r"\bbook\s+[a-zA-Z]+\s+(?:tomorrow|today|at|\d)\b",
    r"\bbook\s+appointment\s+with\b",
    r"\bconfirm\s+appointment\b",
    r"\bappointment\s+at\s+\d",
    r"\bbook\b.*\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
    r"\bbook\s+(?:the\s+)?(?:first|1st|second|2nd|third|3rd|fourth|4th|last)\b",
    r"\b(?:book|reserve|take|confirm)\s+(?:the\s+)?(?:option|slot|doctor|one)\b",
    r"\breschedule\b",
]

# Direct appointment management patterns (cancel, clear, show status)
DIRECT_APPOINTMENT_PATTERNS = [
    r"\bcancel\s+(?:my\s+)?appointment\b",
    r"\bclear\s+(?:my\s+)?appointment\b",
    r"\breset\s+(?:my\s+)?appointment\b",
    r"\bclear\s+summary\b",
    r"\bmy\s+appointment\b",
    r"\bshow\s+appointment\b",
]

SYMPTOM_KEYWORDS = [
    r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bpain\b", r"\bache\b",
    r"\bhurt(s|ing)?\b", r"\bsick\b", r"\bnausea\b", r"\bvomit\b", r"\bdizzy\b",
    r"\bchills\b", r"\btired(ness)?\b", r"\bfatigue\b", r"\bsore\b", r"\brash\b",
    r"\bsymptom(s)?\b", r"\bswollen\b", r"\bcongestion\b", r"\brunny\b",
    r"\btooth\b", r"\bteeth\b", r"\beye(s)?\b", r"\bear(s)?\b",
]

SLOT_BROWSE_KEYWORDS = [
    r"\bphysician\b", r"\bslot(s)?\b", r"\bavailable\s+doctor(s)?\b",
    r"\bfind\s+doctor\b", r"\bevening\b", r"\bmorning\b", r"\bafternoon\b",
    r"\bindiranagar\b", r"\bjayanagar\b", r"\bwhitefield\b", r"\bhsr\b",
    r"\bkoramangala\b", r"\bhebbal\b", r"\bbellandur\b", r"\bbengaluru\b",
    r"\bhospital(s)?\b", r"\bclinic(s)?\b",
]

DEPARTMENT_KEYWORDS = [
    r"\bgeneral\s+medicine\b", r"\bdermatolog(y|ist)\b", r"\bent\b",
    r"\borthopedic(s)?\b", r"\bpediatric(s|ian)?\b", r"\bophthalmolog(y|ist)\b",
    r"\bdental\b", r"\bdentist\b", r"\bclinic\b", r"\bdepartment\b",
]

PATIENT_INFO_PATTERNS = [
    r"\b(set|change|update|edit)\s+(?:my\s+)?name\b",
    r"\bmy\s+name\s+is\b",
    r"\bcall\s+me\s+[a-zA-Z]+\b",
    r"\b(set|change|update|edit)\s+(?:my\s+)?phone\b",
    r"\b(set|change|update|edit)\s+(?:my\s+)?number\b",
    r"\bphone\s+number\b",
    r"\b(set|change|update|edit)\s+(?:my\s+)?age\b",
    r"\b(?:i\s+am|i'm)\s+\d{1,3}\s*(?:years?\s*old|yrs?\s*old)?\b",
    r"\b(set|change|update|edit)\s+(?:my\s+)?preferred\s+department\b",
    r"\bpreferred\s+department\b",
    r"\b(show|view|get|display|check)\s+(?:my\s+)?patient\s+info(?:rmation)?\b",
    r"\bpatient\s+info(?:rmation)?\b",
    r"\b(show|view)\s+(?:my\s+)?(?:profile|details)\b",
]


LOCATION_QUERY_PATTERNS = [
    r"\bnear\s+[a-zA-Z]+",
    r"\bnear\s+me\b",
    r"\bnearby\b",
    r"\bclosest\s+(?:to\s+me|doctor|hospital|clinic)?\b",
    r"\baround\s+[a-zA-Z]+",
    r"\bdoctors?\s+near\b",
    r"\bphysicians?\s+near\b",
    r"\bnearest\b",
    r"\bfind\s+doctors?\s+near\b",
]


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor Agent:
    Evaluates LLM parsed intent & entities, dynamically routing to the appropriate agent:
    - 'final_response': for clarification requests or greetings
    - 'patient_info_agent': demographic/contact management
    - 'location_agent': location-aware / radius-based nearby doctor discovery
    - 'symptom_agent': clinical symptoms (routes -> department -> doctor/slot -> ui_agent)
    - 'doctor_slot_agent': booking, browsing doctors, filtering slots
    - 'appointment_agent': direct cancellation, status, or clearing
    - 'department_agent': explicit department inquiry
    """
    parsed = state.get("parsed_intent") or {}
    intent = parsed.get("intent", "")
    user_msg = state.get("user_message", "").strip().lower()

    if intent == "CLARIFICATION" or parsed.get("needs_clarification"):
        route = "final_response"
    elif intent == "UPDATE_PATIENT":
        route = "patient_info_agent"
    elif intent == "BOOK_APPOINTMENT":
        route = "doctor_slot_agent"
    elif intent == "CANCEL_APPOINTMENT":
        route = "appointment_agent"
    elif intent == "SEARCH_NEARBY":
        route = "location_agent"
    elif intent in ["SEARCH_DOCTOR", "FILTER_SLOTS"]:
        route = "doctor_slot_agent"
    elif intent == "EXTRACT_SYMPTOMS":
        route = "symptom_agent"
    else:
        # Fallback to pattern matching
        is_patient_info = any(re.search(pat, user_msg) for pat in PATIENT_INFO_PATTERNS)
        is_booking_action = any(re.search(pat, user_msg) for pat in BOOKING_ACTION_PATTERNS)
        is_direct_appointment = any(re.search(pat, user_msg) for pat in DIRECT_APPOINTMENT_PATTERNS)
        is_location_query = any(re.search(pat, user_msg) for pat in LOCATION_QUERY_PATTERNS)
        has_symptoms = any(re.search(kw, user_msg) for kw in SYMPTOM_KEYWORDS)
        is_browsing_slots = any(re.search(kw, user_msg) for kw in SLOT_BROWSE_KEYWORDS)
        has_dept = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

        if is_patient_info:
            route = "patient_info_agent"
        elif is_booking_action:
            route = "doctor_slot_agent"
        elif is_direct_appointment:
            route = "appointment_agent"
        elif is_location_query:
            route = "location_agent"
        elif has_symptoms:
            route = "symptom_agent"
        elif is_browsing_slots or ("general physician" in user_msg):
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
    """After symptom extraction, route to department_agent if symptoms exist, else ui_agent."""
    symptoms = state.get("symptoms", [])
    user_msg = state.get("user_message", "").lower()
    has_dept_query = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

    if symptoms or has_dept_query:
        return "department_agent"
    return "ui_agent"


def post_department_router(state: AgentState) -> str:
    """After department suggestion, route to doctor_slot_agent to find available options, else ui_agent."""
    dept = state.get("suggested_department")
    if dept and dept != "Needs clarification":
        return "doctor_slot_agent"
    return "ui_agent"


def post_doctor_slot_router(state: AgentState) -> str:
    """
    After doctor/slot processing:
    - If user wants to book, route to appointment_agent.
    - Otherwise, route to ui_agent to display available doctors/slots on dashboard.
    """
    parsed = state.get("parsed_intent") or {}
    if parsed.get("intent") == "BOOK_APPOINTMENT" or parsed.get("appointment_action") == "BOOK":
        return "appointment_agent"

    user_msg = state.get("user_message", "").lower()
    is_booking = any(re.search(pat, user_msg) for pat in BOOKING_ACTION_PATTERNS)
    if is_booking:
        return "appointment_agent"
    return "ui_agent"


def final_response_node(state: AgentState) -> AgentState:
    """Final synthesis fallback with clarification support and clinical disclaimer."""
    clarification = state.get("clarification_question")
    if clarification:
        return {
            **state,
            "final_response": clarification,
        }

    symptoms = state.get("symptoms", [])
    user_msg = state.get("user_message", "").strip().lower()
    clinical_disclaimer = " (Please note: Only a licensed doctor can provide a medical diagnosis. I am here to help coordinate your checkup and appointments.)"

    if state.get("final_response"):
        resp = state["final_response"]
        if (symptoms or any(k in user_msg for k in ["diagnos", "do i have", "disease", "malaria", "covid"])) and "licensed doctor" not in resp.lower():
            resp += clinical_disclaimer
        return {
            **state,
            "final_response": resp,
        }

    dept = state.get("suggested_department")

    if dept and dept != "Needs clarification":
        final_msg = f"Your request has been routed to {dept}. Please let me know your preferred doctor or time slot."
        if symptoms or any(k in user_msg for k in ["diagnos", "do i have", "disease"]):
            final_msg += clinical_disclaimer
    elif any(g in user_msg for g in ["hello", "hi", "hey"]):
        final_msg = "Hello, how can I help you today? You can describe your symptoms or request an appointment with a doctor."
    else:
        final_msg = "I understand. I can help organize your symptoms and appointment request. Please specify your preferred doctor or time slot."

    return {
        **state,
        "final_response": final_msg,
    }
