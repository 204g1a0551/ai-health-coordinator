import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState
from app.mcp.client import mcp_client
from app.services.provider_service import provider_service
from app.services.redis_service import redis_service
from app.services.llm_service import llm_service
from app.db.repository import revalidate_slot

# Patterns to identify time-of-day preference
PERIOD_PATTERNS = [
    (r"\bevening(s)?\b|\bnight\b|\b5\s*(pm)?\b|\b6\s*(pm)?\b|\b7\s*(pm)?\b", "evening"),
    (r"\bafternoon(s)?\b|\bnoon\b|\b12\s*(pm)?\b|\b1\s*(pm)?\b|\b2\s*(pm)?\b|\b3\s*(pm)?\b|\b4\s*(pm)?\b", "afternoon"),
    (r"\bmorning(s)?\b|\b9\s*(am)?\b|\b10\s*(am)?\b|\b11\s*(am)?\b", "morning"),
]

# Aliases for department matching from appointment phrasing
DEPT_ALIASES = [
    (r"\bhematolog(y|ist)\b|\bplatelet(s)?\b|\bblood\s+doctor\b|\bthrombocytopen(ia|ic)\b|\banemia\b|\bblood\s+specialist\b", "Hematology"),
    (r"\bendocrinolog(y|ist)\b|\bdiabet(es|ic|ologist)\b|\bthyroid\b|\bhormone\s+doctor\b", "Endocrinology"),
    (r"\bnephrolog(y|ist)\b|\bkidney\s+doctor\b|\bkidney\s+specialist\b|\brenal\b|\bdialysis\b", "Nephrology"),
    (r"\bcardiolog(y|ist)\b|\bheart\b|\bcardiac\b", "Cardiology"),
    (r"\bgastroenterolog(y|ist)\b|\bgastro\b|\bstomach\b|\babdominal\b|\bdigestive\b|\bbelly\b|\bacid\s+reflux\b|\bheartburn\b|\bgerd\b", "Gastroenterology"),
    (r"\bpulmonolog(y|ist)\b|\blung(s)?\b|\bchest\s+physician\b|\brespiratory\b|\basthma\b|\bwheez\b|\bbreath\b", "Pulmonology"),
    (r"\bneurolog(y|ist)\b|\bneuro\b|\bbrain\b|\bmigraine\b|\bseizure\b|\bvertigo\b", "Neurology"),
    (r"\bgynecolog(y|ist)\b|\bobstetric(s|ian)?\b|\blady\s+doctor\b|\bmaternity\b|\bpregnan\b|\bperiod\b|\bpcos\b", "Gynecology"),
    (r"\bpsychiatr(y|ist)\b|\bmental\s+health\b|\bcounselor\b|\bpsycholog(y|ist)\b|\bdepress\b|\banxiety\b|\binsomnia\b", "Psychiatry"),
    (r"\bdermatolog(y|ist)\b|\bskin\s+doctor\b|\brash\b|\bskin\b|\bacne\b|\beczema\b", "Dermatology"),
    (r"\bent\b|\bear\s+nose\s+throat\b|\bear(s)?\b|\bthroat\b|\bsinus\b", "ENT"),
    (r"\borthopedic(s|ian)?\b|\bbone\s+doctor\b|\bjoint\b|\bknee\b|\bspine\b|\bback\s+pain\b|\bortho\b", "Orthopedics"),
    (r"\bpediatric(s|ian)?\b|\bchild\s+doctor\b|\bpediatrician\b|\bkid\b|\bbaby\b|\binfant\b", "Pediatrics"),
    (r"\bophthalmolog(y|ist)\b|\beye\s+doctor\b|\bvision\b|\beye(s)?\b", "Ophthalmology"),
    (r"\bdental\b|\bdentist\b|\bteeth\b|\btooth\b|\btoothache\b|\bgum\b", "Dental"),
    (r"\bgeneral\s+physician\b|\bphysician\b|\bgeneral\s+doctor\b|\bgp\b|\bgeneral\s+medicine\b|\binternal\s+medicine\b", "General Medicine"),
]

# Bengaluru localities and neighborhood patterns
LOCALITY_PATTERNS = [
    (r"\bindiranagar\b", "Indiranagar"),
    (r"\bjayanagar\b", "Jayanagar"),
    (r"\bwhitefield\b", "Whitefield"),
    (r"\bhsr(\s+layout)?\b", "HSR Layout"),
    (r"\bkoramangala\b", "Koramangala"),
    (r"\bhebbal\b", "Hebbal"),
    (r"\bbellandur\b|\bouter\s+ring\s+road\b", "Bellandur"),
    (r"\bcunningham(\s+road)?\b|\bvasanth\s+nagar\b", "Cunningham Road"),
    (r"\bbannerghatta(\s+road)?\b", "Bannerghatta Road"),
    (r"\bold\s+airport\s+road\b|\bhal\b", "Old Airport Road"),
]


def extract_period_preference(text: str) -> Optional[str]:
    """Extract preferred time of day (morning, afternoon, evening) from text."""
    lower_text = text.lower()
    for pattern, period in PERIOD_PATTERNS:
        if re.search(pattern, lower_text):
            return period
    return None


def extract_date_preference(text: str) -> str:
    """Extract date preference from user message or default to Tomorrow."""
    lower_text = text.lower()
    if "today" in lower_text:
        return "Today, Oct 23"
    elif "tomorrow" in lower_text:
        return "Tomorrow, Oct 24"
    return "Tomorrow, Oct 24"


def extract_locality_preference(text: str) -> Optional[str]:
    """Extract Bengaluru locality/area from user query."""
    lower_text = text.lower()
    for pattern, locality in LOCALITY_PATTERNS:
        if re.search(pattern, lower_text):
            return locality
    return None


def resolve_department_for_booking(state: AgentState) -> str:
    """Determine department for doctor search from state or user message."""
    dept = state.get("suggested_department")
    if dept and dept != "Needs clarification":
        return dept

    user_msg = state.get("user_message", "").lower()
    for pattern, dept_name in DEPT_ALIASES:
        if re.search(pattern, user_msg):
            return dept_name

    # Check if doctor name mentioned directly
    doc_match = re.search(r"\b(?:dr\.?|doctor)\s+([a-zA-Z]+)", user_msg)
    if doc_match:
        doc_details = provider_service.get_doctor_details(doc_match.group(1))
        if doc_details and doc_details.get("department"):
            return doc_details["department"]

    return "General Medicine"


def doctor_slot_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Doctor/Slot Agent
    Calls controlled backend tools from HealthcareProviderService (cached via Redis).
    Does NOT allow the LLM to directly communicate with external APIs.
    """
    user_msg = state.get("user_message", "")
    parsed_intent = state.get("parsed_intent") or {}

    # Prioritize suggested_department from symptom/department agent if available
    suggested = state.get("suggested_department")
    if suggested and suggested != "Needs clarification":
        target_dept = suggested
    elif parsed_intent.get("department") and parsed_intent["department"] != "General Medicine":
        target_dept = parsed_intent["department"]
    else:
        target_dept = resolve_department_for_booking(state)

    period_pref = parsed_intent.get("time") or extract_period_preference(user_msg)
    date_pref = parsed_intent.get("date") or extract_date_preference(user_msg)

    locality_pref = None
    if parsed_intent.get("location"):
        locality_pref = parsed_intent["location"].replace(", Bengaluru", "").strip()
    if not locality_pref:
        locality_pref = extract_locality_preference(user_msg)

    # 1. Controlled Backend Tool Call: search_doctors via provider_service
    multi_depts = state.get("multi_departments") or []
    target_depts = [d["department"] for d in multi_depts] if multi_depts else [target_dept]

    unique_depts = []
    for d in target_depts:
        if d and d not in unique_depts and d != "General Medicine":
            unique_depts.append(d)
    if not unique_depts:
        unique_depts = [target_dept]

    doctors_found = []
    session_id = state.get("session_id", "default")
    user_id = state.get("user_id")

    for dept_to_search in unique_depts:
        dept_docs = []
        if locality_pref:
            mcp_res = mcp_client.call_tool(
                server_name="doctor_mcp",
                tool_name="search_by_location",
                arguments={"location": locality_pref, "department": dept_to_search},
                caller_agent="doctor_slot_agent",
                session_id=session_id,
                user_id=user_id,
            )
            if mcp_res.success and mcp_res.data:
                dept_docs = mcp_res.data.get("doctors", [])
        if not dept_docs:
            mcp_res = mcp_client.call_tool(
                server_name="doctor_mcp",
                tool_name="search_by_department",
                arguments={"department": dept_to_search, "location": locality_pref},
                caller_agent="doctor_slot_agent",
                session_id=session_id,
                user_id=user_id,
            )
            if mcp_res.success and mcp_res.data:
                dept_docs = mcp_res.data.get("doctors", [])
        # Include top verified specialists for each matched department
        limit = 2 if len(unique_depts) > 1 else 4
        doctors_found.extend(dept_docs[:limit])

    # Fallback to general search if department had zero doctors
    if not doctors_found:
        mcp_res = mcp_client.call_tool(
            server_name="doctor_mcp",
            tool_name="search_doctors",
            arguments={"query": None},
            caller_agent="doctor_slot_agent",
            session_id=session_id,
            user_id=user_id,
        )
        if mcp_res.success and mcp_res.data:
            doctors_found = mcp_res.data.get("doctors", [])[:4]

    current_timestamp = datetime.utcnow().strftime("%d %b %Y, %I:%M %p")
    provider_name = provider_service.provider.provider_name

    structured_doctors = []
    flat_slots = []
    flat_doctor_cards = []

    for d in doctors_found:
        # 2. Controlled MCP Tool Call: Query appointment_mcp for real-time slots
        slot_res = mcp_client.call_tool(
            server_name="appointment_mcp",
            tool_name="get_available_slots",
            arguments={"doctor_id": d["id"], "date": date_pref, "period": period_pref},
            caller_agent="doctor_slot_agent",
            session_id=session_id,
            user_id=user_id,
        )
        slots = slot_res.data.get("slots", []) if slot_res.success and slot_res.data else []
        if period_pref and slots:
            slots = [s for s in slots if s.get("period") == period_pref]

        # Real-time database availability & lock check: mark slot unavailable if booked or locked
        current_session = state.get("session_id", "")
        for s in slots:
            # 1. Check database availability
            slot_check = revalidate_slot(d["id"], s["time"])
            if not slot_check.get("is_available", True):
                s["isAvailable"] = False

            # 2. Check active concurrency lock
            lock_holder = redis_service.is_slot_locked(d["id"], date_pref, s["time"])
            if lock_holder and lock_holder != current_session:
                s["isAvailable"] = False

        slot_times = [s["time"] for s in slots if s.get("isAvailable", True)]

        structured_doctors.append({
            "name": d["name"],
            "department": d["department"],
            "hospital": d.get("hospital", "Bengaluru Healthcare Center"),
            "locality": d.get("locality", "Bengaluru"),
            "slots": slot_times,
        })

        flat_doctor_cards.append({
            "id": d["id"],
            "name": d["name"],
            "department": d["department"],
            "availableStatus": d.get("availableStatus", "Available"),
            "hospital": d.get("hospital", "Bengaluru Hospital"),
            "clinic": d.get("clinic", "Specialty Clinic"),
            "locality": d.get("locality", "Bengaluru"),
            "address": d.get("address", "Bengaluru, Karnataka"),
            "consultationFee": d.get("consultationFee", "₹600"),
            "consultationType": d.get("consultationType", "In-Person"),
            "experience": d.get("experience", "10+ yrs exp"),
            "rating": d.get("rating", 4.8),
            "dataSource": provider_name,
            "timestamp": current_timestamp,
            "slots": slot_times,
        })

        for s in slots:
            flat_slots.append({
                "id": s["id"],
                "doctor": d["name"],
                "department": d["department"],
                "hospital": d.get("hospital", "Hospital"),
                "locality": d.get("locality", "Bengaluru"),
                "date": s.get("date", date_pref),
                "time": s["time"],
                "isAvailable": bool(s.get("isAvailable", True)),
                "dataSource": provider_name,
                "timestamp": current_timestamp,
            })

    structured_result = {
        "department": target_dept,
        "locality": locality_pref,
        "doctors": structured_doctors,
        "dataSource": provider_name,
        "timestamp": current_timestamp,
    }

    actions = list(state.get("actions", []))

    # Also make sure the Suggested Department on the dashboard is updated
    if not any(a.get("type") == "UPDATE_DEPARTMENT" for a in actions):
        actions.append({
            "type": "UPDATE_DEPARTMENT",
            "payload": {
                "department": target_dept,
                "reason": f"Consultation search for {target_dept}" + (f" in {locality_pref}." if locality_pref else "."),
            }
        })

    # Emit structured action to update left dashboard
    if flat_doctor_cards and flat_slots:
        actions.append({
            "type": "UPDATE_DOCTORS_AND_SLOTS",
            "action": "SHOW_DOCTORS",
            "payload": {
                "department": target_dept,
                "locality": locality_pref,
                "date": date_pref,
                "doctors": flat_doctor_cards,
                "slots": flat_slots,
                "dataSource": provider_name,
                "timestamp": current_timestamp,
            }
        })
        actions.append({
            "type": "SHOW_DOCTORS",
            "action": "SHOW_DOCTORS",
            "payload": {
                "department": target_dept,
                "locality": locality_pref,
                "date": date_pref,
                "doctors": flat_doctor_cards,
                "slots": flat_slots,
                "dataSource": provider_name,
                "timestamp": current_timestamp,
            }
        })

    # Persist last shown options into Redis session context for ordinal/follow-up requests (e.g. "Book the second option")
    session_id = state.get("session_id", "default")
    options_for_context = []
    for idx, d in enumerate(structured_doctors):
        primary_slot = d["slots"][0] if d.get("slots") else "10:00 AM"
        options_for_context.append({
            "index": idx + 1,
            "doctor": d["name"],
            "department": d["department"],
            "hospital": d.get("hospital", "Bengaluru Hospital"),
            "locality": d.get("locality", "Bengaluru"),
            "time": primary_slot,
            "date": date_pref,
        })

    llm_service.update_conversation_context(session_id, {
        "last_shown_options": options_for_context,
        "department": target_dept,
        "location": locality_pref,
        "date": date_pref,
    })

    return {
        **state,
        "suggested_department": target_dept,
        "doctor_slot_results": structured_result,
        "actions": actions,
    }
