import re
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState
from app.db.repository import query_doctors_and_slots
from app.services.redis_service import redis_service

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


def resolve_department_for_booking(state: AgentState) -> str:
    """Determine department for doctor search from state or user message."""
    dept = state.get("suggested_department")
    if dept and dept != "Needs clarification":
        return dept

    user_msg = state.get("user_message", "").lower()
    for pattern, dept_name in DEPT_ALIASES:
        if re.search(pattern, user_msg):
            return dept_name

    return "General Medicine"


def doctor_slot_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Doctor/Slot Agent
    Searches available doctors and slots based on department and time preference,
    returning structured data and UI update actions.
    """
    user_msg = state.get("user_message", "")
    target_dept = resolve_department_for_booking(state)
    period_pref = extract_period_preference(user_msg)
    date_pref = extract_date_preference(user_msg)

    cache_key = f"{target_dept}:{period_pref or 'all'}"
    doctors_found = redis_service.get_hospital_doctors(hospital_id=cache_key)
    if not doctors_found:
        doctors_found = query_doctors_and_slots(target_dept, period_pref)
        redis_service.set_hospital_doctors(hospital_id=cache_key, doctors=doctors_found)

    # Cache individual doctor availability in Redis
    for d in doctors_found:
        redis_service.set_doctor_availability(
            doctor_id=d["id"],
            availability_data={
                "name": d["name"],
                "department": d["department"],
                "status": d["availableStatus"],
                "slots": d["slots"],
            },
        )

    # Format structured results matching the specification
    structured_doctors = []
    flat_slots = []
    flat_doctor_cards = []

    for d in doctors_found:
        structured_doctors.append({
            "name": d["name"],
            "slots": d["slots"],
        })
        flat_doctor_cards.append({
            "id": d["id"],
            "name": d["name"],
            "department": d["department"],
            "availableStatus": d["availableStatus"],
        })
        for s in d["slotsDetails"]:
            flat_slots.append(s)

    structured_result = {
        "department": target_dept,
        "doctors": structured_doctors,
    }

    actions = list(state.get("actions", []))

    # Also make sure the Suggested Department on the dashboard is updated
    if not any(a.get("type") == "UPDATE_DEPARTMENT" for a in actions):
        actions.append({
            "type": "UPDATE_DEPARTMENT",
            "payload": {
                "department": target_dept,
                "reason": f"Directly matched from appointment request for {target_dept}."
            }
        })

    # Emit structured action to update left dashboard
    if flat_doctor_cards and flat_slots:
        actions.append({
            "type": "UPDATE_DOCTORS_AND_SLOTS",
            "payload": {
                "department": target_dept,
                "date": date_pref,
                "doctors": flat_doctor_cards,
                "slots": flat_slots,
            }
        })

    return {
        **state,
        "suggested_department": target_dept,
        "doctor_slot_results": structured_result,
        "actions": actions,
    }
