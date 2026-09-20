import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState
from app.services.provider_service import provider_service
from app.services.redis_service import redis_service
from app.services.llm_service import llm_service

# Patterns to identify time-of-day preference
PERIOD_PATTERNS = [
    (r"\bevening(s)?\b|\bnight\b|\b5\s*(pm)?\b|\b6\s*(pm)?\b|\b7\s*(pm)?\b", "evening"),
    (r"\bafternoon(s)?\b|\bnoon\b|\b12\s*(pm)?\b|\b1\s*(pm)?\b|\b2\s*(pm)?\b|\b3\s*(pm)?\b|\b4\s*(pm)?\b", "afternoon"),
    (r"\bmorning(s)?\b|\b9\s*(am)?\b|\b10\s*(am)?\b|\b11\s*(am)?\b", "morning"),
]

# Aliases for department matching from appointment phrasing
DEPT_ALIASES = [
    (r"\bgeneral\s+physician\b|\bphysician\b|\bgeneral\s+doctor\b|\bgp\b", "General Medicine"),
    (r"\bdermatolog(y|ist)\b|\bskin\s+doctor\b", "Dermatology"),
    (r"\bent\b|\bear\s+nose\s+throat\b", "ENT"),
    (r"\borthopedic(s|ian)?\b|\bbone\s+doctor\b", "Orthopedics"),
    (r"\bpediatric(s|ian)?\b|\bchild\s+doctor\b", "Pediatrics"),
    (r"\bophthalmolog(y|ist)\b|\beye\s+doctor\b", "Ophthalmology"),
    (r"\bdental\b|\bdentist\b", "Dental"),
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

    # Read from parsed_intent first (if LLM extracted it), fallback to regex
    target_dept = parsed_intent.get("department") or resolve_department_for_booking(state)
    period_pref = parsed_intent.get("time") or extract_period_preference(user_msg)
    date_pref = parsed_intent.get("date") or extract_date_preference(user_msg)

    locality_pref = None
    if parsed_intent.get("location"):
        locality_pref = parsed_intent["location"].replace(", Bengaluru", "").strip()
    if not locality_pref:
        locality_pref = extract_locality_preference(user_msg)

    # 1. Controlled Backend Tool Call: search_doctors via provider_service
    doctors_found = []
    if locality_pref:
        doctors_found = provider_service.search_by_location(locality=locality_pref, department=target_dept)

    if not doctors_found:
        doctors_found = provider_service.search_by_department(department=target_dept)

    # Fallback to general search if department had zero doctors
    if not doctors_found:
        doctors_found = provider_service.search_doctors(query=None)

    current_timestamp = datetime.utcnow().strftime("%d %b %Y, %I:%M %p")
    provider_name = provider_service.provider.provider_name

    structured_doctors = []
    flat_slots = []
    flat_doctor_cards = []

    for d in doctors_found:
        # 2. Controlled Backend Tool Call: get_available_slots via provider_service
        slots = provider_service.get_available_slots(
            doctor_id=d["id"],
            date=date_pref,
            period=period_pref,
        )

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
