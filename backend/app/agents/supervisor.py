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
    r"\bplatelet(s)?\b", r"\bthrombocytopen(ia|ic)\b", r"\bhemoglobin\b", r"\banemia\b", r"\bbruis(ing|e)?\b",
    r"\bheart\s*attack\b", r"\bcardiac\b", r"\bchest\s+pain\b", r"\bchest\s+tightness\b", r"\bpalpitation(s)?\b",
    r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bpain\b", r"\bache\b",
    r"\bhurt(s|ing)?\b", r"\bsick\b", r"\bnausea\b", r"\bvomit\b", r"\bdizzy\b",
    r"\bchills\b", r"\btired(ness)?\b", r"\bfatigue\b", r"\bsore\b", r"\brash\b",
    r"\bsymptom(s)?\b", r"\bswollen\b", r"\bcongestion\b", r"\brunny\b",
    r"\btooth\b", r"\bteeth\b", r"\beye(s)?\b", r"\bear(s)?\b",
    r"\bstomach\b", r"\babdominal\b", r"\bbelly\b", r"\bacid\s+reflux\b", r"\bheartburn\b",
    r"\basthma\b", r"\bwheez(ing)?\b", r"\bbreath(less|ing)?\b", r"\bmigraine\b",
    r"\bseizure\b", r"\bdepress(ion)?\b", r"\banxiety\b",
    r"\bblood\s+sugar\b", r"\bdiabet(es|ic)\b", r"\bhba1c\b", r"\bthyroid\b", r"\btsh\b",
    r"\bcreatinine\b", r"\bkidney\b", r"\bflank\s+pain\b", r"\burnt\b",
]

SLOT_BROWSE_KEYWORDS = [
    r"\bphysician\b", r"\bslot(s)?\b", r"\bavailable\s+doctor(s)?\b",
    r"\bfind\s+doctor\b", r"\bevening\b", r"\bmorning\b", r"\bafternoon\b",
    r"\bindiranagar\b", r"\bjayanagar\b", r"\bwhitefield\b", r"\bhsr\b",
    r"\bkoramangala\b", r"\bhebbal\b", r"\bbellandur\b", r"\bbengaluru\b",
    r"\bhospital(s)?\b", r"\bclinic(s)?\b",
]

DEPARTMENT_KEYWORDS = [
    r"\bhematolog(y|ist)\b", r"\bplatelet(s)?\b",
    r"\bendocrinolog(y|ist)\b", r"\bdiabet(es|ologist)\b",
    r"\bnephrolog(y|ist)\b", r"\bkidney\b",
    r"\bcardiolog(y|ist)\b", r"\bheart\b", r"\bcardiac\b",
    r"\bgastroenterolog(y|ist)\b", r"\bgastro\b", r"\bdigestive\b",
    r"\bneurolog(y|ist)\b", r"\bneuro\b",
    r"\bpulmonolog(y|ist)\b", r"\brespiratory\b", r"\blung\b",
    r"\bgynecolog(y|ist)\b", r"\bmaternity\b",
    r"\bpsychiatr(y|ist)\b", r"\bmental\s+health\b",
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

PHARMACY_PATTERNS = [
    r"\b(?:where\s+can\s+i\s+get|buy|find|purchase)\s+(?:the\s+)?medicines?\b",
    r"\bwhere\s+(?:to|can\s+i)\s+get\s+(?:medicines?|prescription)\b",
    r"\bpharmacy\b|\bpharmacies\b|\bchemist\b|\bmedical\s+store\b|\bdrugstore\b",
    r"\bprescribed\s+medicines?\b",
    r"\bget\s+(?:the\s+)?medicines?\s+from\s+(?:this\s+)?prescription\b",
    r"\bmedicines?\s+(?:from\s+)?(?:the\s+)?prescription\b",
]

INSURANCE_PATTERNS = [
    r"\b(?:covered|coverage|reimburse|reimbursement|insurance\s+policy|company\s+policy|reimbursement\s+policy)\b",
    r"\bwill\s+(?:this|my)\s+(?:medicine|bill|expenses?|claim)\s+be\s+covered\b",
    r"\baccording\s+to\s+my\s+(?:company\s+)?policy\b",
    r"\bdoes\s+my\s+(?:company\s+)?policy\s+mention\b",
    r"\bwhat\s+does\s+(?:my\s+)?insurance\s+policy\s+say\b",
    r"\bclaim\s+submission\s+deadline\b",
]


def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor Agent:
    Evaluates LLM parsed intent & entities, dynamically routing to the appropriate agent:
    - 'final_response': for clarification requests or greetings
    - 'insurance_agent': insurance & reimbursement policy coverage analysis
    - 'patient_info_agent': demographic/contact management
    - 'location_agent': location-aware / radius-based nearby doctor discovery
    - 'medicine_search_agent': medicine & nearby pharmacy store search
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
    elif intent in ["ANALYZE_INSURANCE", "CHECK_COVERAGE", "CHECK_REIMBURSEMENT"]:
        route = "insurance_agent"
    elif intent in ["SEARCH_PHARMACY", "SEARCH_MEDICINE"]:
        route = "medicine_search_agent"
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
        is_insurance_query = any(re.search(pat, user_msg) for pat in INSURANCE_PATTERNS)
        is_pharmacy_query = any(re.search(pat, user_msg) for pat in PHARMACY_PATTERNS)
        is_patient_info = any(re.search(pat, user_msg) for pat in PATIENT_INFO_PATTERNS)
        is_booking_action = any(re.search(pat, user_msg) for pat in BOOKING_ACTION_PATTERNS)
        is_direct_appointment = any(re.search(pat, user_msg) for pat in DIRECT_APPOINTMENT_PATTERNS)
        is_location_query = any(re.search(pat, user_msg) for pat in LOCATION_QUERY_PATTERNS)
        has_symptoms = any(re.search(kw, user_msg) for kw in SYMPTOM_KEYWORDS)
        is_browsing_slots = any(re.search(kw, user_msg) for kw in SLOT_BROWSE_KEYWORDS)
        has_dept = any(re.search(kw, user_msg) for kw in DEPARTMENT_KEYWORDS)

        if is_insurance_query:
            route = "insurance_agent"
        elif is_pharmacy_query:
            route = "medicine_search_agent"
        elif is_patient_info:
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
    """Final synthesis fallback with emergency red-flag interceptor, clarification support, and clinical disclaimer."""
    user_msg = state.get("user_message", "").strip().lower()

    # 1. Emergency Red-Flag Interceptor (Heart attack, stroke, acute trauma)
    is_cardiac_emergency = bool(re.search(r"\b(?:heart\s*attack|cardiac\s+arrest|myocardial\s+infarction|severe\s+chest\s+pain|chest\s+tightness|chest\s+pressure)\b", user_msg))
    is_stroke_emergency = bool(re.search(r"\b(?:stroke|face\s+droop|arm\s+weakness|paralysis)\b", user_msg))
    is_acute_emergency = bool(re.search(r"\b(?:unconscious|not\s+breathing|choking|heavy\s+bleeding|severe\s+bleeding|poisoning|anaphylaxis)\b", user_msg))

    if is_cardiac_emergency or is_stroke_emergency or is_acute_emergency:
        emergency_msg = (
            "🚨 **CRITICAL MEDICAL EMERGENCY WARNING**:\n\n"
            "If you or someone with you is experiencing symptoms of a **heart attack**, **stroke**, or acute medical emergency, "
            "**IMMEDIATELY call Emergency Services (108 / 112 in India, or 911) or proceed to the nearest Hospital Emergency Room right now!**\n\n"
            "⚠️ **Do NOT wait for a routine clinic appointment.** Immediate emergency medical intervention is crucial.\n\n"
            "**Immediate 24x7 Emergency Cardiac Centers in Bengaluru:**\n"
            "• **Manipal Hospital Emergency & Cardiac Care**: 080 2502 4444 (Old Airport Road / Indiranagar)\n"
            "• **Apollo Hospital Emergency Department**: 080 2630 4050 (Bannerghatta Road / Jayanagar)\n"
            "• **Fortis Hospital 24x7 Emergency**: 080 4199 4444 (Cunningham Road / Central Bengaluru)\n"
            "• **Aster CMI Hospital Emergency**: 080 4342 0100 (Hebbal)\n\n"
            "I have prioritized and routed your consultation request to **Cardiology / Emergency Care**.\n\n"
            "**Available verified Cardiologists for urgent evaluation:**\n"
            "• **Dr. Anand Shenoy** (Manipal Heart & Vascular Institute, Indiranagar) — Available slots: **09:00 AM, 11:00 AM, 05:00 PM**\n"
            "• **Dr. Deepak Krishnamurthy** (Fortis Cardiac Care Center, Cunningham Road) — Available slots: **10:00 AM, 04:00 PM, 06:00 PM**"
        )
        return {
            **state,
            "suggested_department": "Cardiology",
            "final_response": emergency_msg,
        }

    clarification = state.get("clarification_question")
    if clarification:
        return {
            **state,
            "final_response": clarification,
        }

    symptoms = state.get("symptoms", [])
    clinical_disclaimer = "\n\n*(Please note: Only a licensed doctor can provide a medical diagnosis. I am here to help coordinate your checkup and appointments.)*"

    if state.get("final_response"):
        resp = state["final_response"]
        if (symptoms or any(k in user_msg for k in ["diagnos", "do i have", "disease", "malaria", "covid"])) and "licensed doctor" not in resp.lower():
            resp += clinical_disclaimer
        return {
            **state,
            "final_response": resp,
        }

    dept = state.get("suggested_department")
    ds_res = state.get("doctor_slot_results") or {}
    docs = ds_res.get("doctors", [])
    multi_depts = state.get("multi_departments") or []

    if len(multi_depts) > 1 and docs:
        dept_docs: Dict[str, List[Dict[str, Any]]] = {}
        for d in docs:
            dept_docs.setdefault(d.get("department", "Specialty"), []).append(d)

        icons = {
            "Gynecology": "🌸",
            "Psychiatry": "🧠",
            "Orthopedics": "🦴",
            "Cardiology": "❤️",
            "Gastroenterology": "🩺",
            "Pulmonology": "🫁",
            "Neurology": "⚡",
            "Dermatology": "🧴",
            "ENT": "👂",
            "Dental": "🦷",
            "Ophthalmology": "👁️",
            "Hematology": "🩸",
            "Endocrinology": "🧬",
            "Nephrology": "💧",
            "Pediatrics": "👶",
            "General Medicine": "🏥",
        }

        sections = []
        for md in multi_depts:
            m_dept = md.get("department")
            if not m_dept or m_dept == "General Medicine":
                continue
            m_kw = md.get("matchedKeyword", "")
            icon = icons.get(m_dept, "•")
            lines = [f"{icon} **{m_dept}**" + (f" (for *{m_kw}*):" if m_kw else ":")]
            m_docs = dept_docs.get(m_dept, [])[:2]
            if m_docs:
                for d in m_docs:
                    slots_str = ", ".join(d["slots"][:3]) if d.get("slots") else "Contact clinic for slots"
                    lines.append(f"  • **{d['name']}** ({d.get('hospital', 'Bengaluru Hospital')}) — Available slots: **{slots_str}**")
            else:
                lines.append(f"  • Verified {m_dept} specialists are on duty.")
            sections.append("\n".join(lines))

        final_msg = (
            f"I noticed your inquiry covers **{len(sections)} different healthcare specialties**:\n\n"
            + "\n\n".join(sections)
            + "\n\nWould you like me to book one of these slots for you, or which condition would you like to prioritize first?"
        )
        if symptoms or any(k in user_msg for k in ["diagnos", "do i have", "disease"]):
            final_msg += clinical_disclaimer
    elif dept and dept != "Needs clarification":
        if docs:
            doc_lines = []
            for d in docs[:3]:
                slots_str = ", ".join(d["slots"][:3]) if d.get("slots") else "Contact clinic for slots"
                loc = d.get("locality") or d.get("hospital", "Bengaluru")
                doc_lines.append(f"• **{d['name']}** ({d['hospital']}, {loc}) — Available slots: **{slots_str}**")

            final_msg = (
                f"Your request has been routed to **{dept}**.\n\n"
                f"Here are the available verified specialists and their real-time consultation slots:\n"
                + "\n".join(doc_lines)
                + "\n\nWould you like me to book one of these slots for you, or do you have a preferred time?"
            )
        else:
            final_msg = f"Your request has been routed to **{dept}**. Please let me know your preferred doctor or time slot."

        if symptoms or any(k in user_msg for k in ["diagnos", "do i have", "disease"]):
            final_msg += clinical_disclaimer
    elif symptoms:
        final_msg = "I have noted your symptoms. Could you provide a bit more detail or your preferred medical specialty (e.g. Cardiology, Gastroenterology, Pulmonology, Neurology, Orthopedics, ENT, Dermatology, or General Medicine)?"
    elif any(g in user_msg for g in ["hello", "hi", "hey"]):
        final_msg = "Hello, how can I help you today? You can describe your symptoms or request an appointment with a doctor."
    else:
        final_msg = "I understand. I can help organize your symptoms and appointment request. Please specify your preferred doctor or medical department."

    return {
        **state,
        "final_response": final_msg,
    }
