import re
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState, UIAction
from app.services.provider_service import provider_service
from app.db.repository import get_patient_info, find_doctor_by_name

# Predefined allowed controlled actions
ALLOWED_ACTIONS = {
    "SHOW_WELCOME",
    "SHOW_PATIENT_INFO",
    "SHOW_SYMPTOMS",
    "SHOW_DEPARTMENT",
    "SHOW_DOCTORS",
    "SHOW_DOCTOR_DETAILS",
    "SHOW_SLOTS",
    "SHOW_NEARBY_DOCTORS",
    "SHOW_PHARMACIES",
    "SHOW_APPOINTMENT",
    "HIDE_COMPONENT",
    "CLEAR_DASHBOARD",
    # Legacy / alias compatibility
    "UPDATE_SYMPTOMS",
    "UPDATE_DEPARTMENT",
    "UPDATE_PATIENT",
    "BOOK_APPOINTMENT",
    "CANCEL_APPOINTMENT",
    "CLEAR_APPOINTMENT",
    "REQUEST_LOCATION_PERMISSION",
}

# Dangerous patterns to reject from LLM / payload injection
UNSAFE_PATTERNS = [
    r"<script\b[^>]*>",
    r"javascript:",
    r"onerror\s*=",
    r"onload\s*=",
    r"<style\b[^>]*>",
    r"eval\(",
    r"document\.",
    r"window\.",
]


def is_safe_payload(val: Any) -> bool:
    """Recursively checks that payload contains no executable script or DOM injections."""
    if isinstance(val, str):
        for pat in UNSAFE_PATTERNS:
            if re.search(pat, val, re.IGNORECASE):
                return False
        return True
    elif isinstance(val, dict):
        return all(is_safe_payload(k) and is_safe_payload(v) for k, v in val.items())
    elif isinstance(val, list):
        return all(is_safe_payload(item) for item in val)
    return True


def create_ui_action(action_name: str, payload: Dict[str, Any]) -> Optional[UIAction]:
    """
    Creates a controlled UI action if it belongs to the allowed specification
    and contains safe data.
    """
    if action_name not in ALLOWED_ACTIONS:
        return None

    if not is_safe_payload(payload):
        return None

    return {
        "action": action_name,
        "data": payload,
        "payload": payload,
        "type": action_name,
    }


def ui_action_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: UI Agent / UI Action Layer
    Consolidates domain agent results into a single controlled, safe, structured UI action.
    The left dashboard behaves like a dynamic canvas showing ONE relevant piece of healthcare
    information at a time based on the active conversation turn.
    """
    raw_actions = state.get("actions", [])
    symptoms = state.get("symptoms", [])
    dept = state.get("suggested_department") or "General Medicine"
    dept_reason = state.get("department_reason") or f"Routed consultation for {dept}."
    parsed = state.get("parsed_intent") or {}
    intent = parsed.get("intent", "")
    user_msg = state.get("user_message", "").strip().lower()
    session_id = state.get("session_id", "default")

    primary_action = "SHOW_WELCOME"
    primary_data: Dict[str, Any] = {}

    # --------------------------------------------------------------------------
    # 1. Clear / Reset / Welcome Request
    # --------------------------------------------------------------------------
    if any(k in user_msg for k in ["clear dashboard", "clear canvas", "reset dashboard", "hide component"]):
        primary_action = "CLEAR_DASHBOARD"
        primary_data = {"message": "Dashboard cleared"}

    # --------------------------------------------------------------------------
    # 1.5. Pharmacy & Medicine Search
    # --------------------------------------------------------------------------
    elif (
        any(a.get("action") == "SHOW_PHARMACIES" or a.get("type") == "SHOW_PHARMACIES" for a in raw_actions)
        or state.get("pharmacy_results")
        or intent in ["SEARCH_PHARMACY", "SEARCH_MEDICINE"]
    ):
        primary_action = "SHOW_PHARMACIES"
        pharm_act = next(
            (a for a in raw_actions if a.get("action") == "SHOW_PHARMACIES" or a.get("type") == "SHOW_PHARMACIES"),
            None
        )
        if pharm_act:
            primary_data = pharm_act.get("payload") or pharm_act.get("data") or {}
        else:
            primary_data = state.get("pharmacy_results") or {}

    # --------------------------------------------------------------------------
    # 2. Appointment Booking / Confirmation
    # --------------------------------------------------------------------------
    elif (
        intent == "BOOK_APPOINTMENT"
        or any(a.get("action") == "BOOK_APPOINTMENT" or a.get("type") == "BOOK_APPOINTMENT" for a in raw_actions)
        or any(k in user_msg for k in ["book ", "confirm appointment", "reserve "])
    ):
        # Extract appointment details from raw actions or state
        appt_action = next(
            (a for a in raw_actions if a.get("action") in ["BOOK_APPOINTMENT", "SHOW_APPOINTMENT"] or a.get("type") in ["BOOK_APPOINTMENT", "SHOW_APPOINTMENT"]),
            None
        )
        if appt_action:
            p = appt_action.get("payload") or appt_action.get("data") or {}
            appt = p.get("appointment") or p
            primary_action = "SHOW_APPOINTMENT"
            primary_data = {
                "doctor": appt.get("doctor", "Dr. Ravi Kumar"),
                "department": appt.get("department", dept),
                "date": appt.get("date") or appt.get("displayDate") or "Tomorrow",
                "time": appt.get("time") or appt.get("displayTime") or "6:30 PM",
                "status": appt.get("status", "Confirmed"),
            }
        else:
            primary_action = "SHOW_APPOINTMENT"
            primary_data = {
                "doctor": parsed.get("doctor") or "Dr. Ravi Kumar",
                "department": dept,
                "date": parsed.get("date") or "Tomorrow",
                "time": parsed.get("time") or "6:30 PM",
                "status": "Confirmed",
            }

    # --------------------------------------------------------------------------
    # 3. Available Slots Inquiry ("Show available slots for Dr. Ravi", "Show his slots")
    # --------------------------------------------------------------------------
    elif (
        intent == "FILTER_SLOTS"
        or any(k in user_msg for k in ["slot", "slots", "availability", "available time", "show his slots"])
        or any(a.get("action") == "SHOW_SLOTS" or a.get("type") == "SHOW_SLOTS" for a in raw_actions)
    ):
        primary_action = "SHOW_SLOTS"
        doc_name = parsed.get("doctor") or "Dr. Ravi Kumar"
        # Match doctor from message if explicitly mentioned
        doc_match = re.search(r"\b(?:dr\.?|doctor)\s+([a-zA-Z]+)", user_msg, re.IGNORECASE)
        if doc_match:
            doc_info = find_doctor_by_name(doc_match.group(1))
            if doc_info:
                doc_name = doc_info["name"]

        # Find slots from raw actions or provider
        slots_found = []
        for a in raw_actions:
            p = a.get("payload") or a.get("data") or {}
            if "slots" in p and isinstance(p["slots"], list):
                slots_found = p["slots"]
                break

        if not slots_found:
            doc_id = "doc-ravi"
            if "priya" in doc_name.lower():
                doc_id = "doc-priya"
            elif "arun" in doc_name.lower():
                doc_id = "doc-arun"
            raw_slots = provider_service.get_available_slots(doc_id)
            slots_found = [s["time"] for s in raw_slots if s.get("isAvailable", True)]

        # Extract string time slots
        formatted_slots = [
            s["time"] if isinstance(s, dict) and "time" in s else str(s)
            for s in slots_found
        ]
        if not formatted_slots:
            formatted_slots = ["5:30 PM", "6:30 PM"]

        primary_data = {
            "doctor": doc_name,
            "department": dept,
            "date": parsed.get("date") or "Tomorrow, Oct 24",
            "slots": formatted_slots,
        }

    # --------------------------------------------------------------------------
    # 4. Doctor Details Inquiry ("Show Dr. Ravi", "Details of Dr. Priya")
    # --------------------------------------------------------------------------
    elif (
        re.search(r"\b(?:show|view|details|about|who is)\s+(?:dr\.?|doctor)\s+[a-zA-Z]+", user_msg, re.IGNORECASE)
        or (re.search(r"^(?:show\s+)?dr\.?\s+[a-zA-Z]+$", user_msg, re.IGNORECASE))
    ):
        doc_match = re.search(r"\b(?:dr\.?|doctor)\s+([a-zA-Z]+)", user_msg, re.IGNORECASE)
        doc_query = doc_match.group(1) if doc_match else "Ravi"
        doc_details = provider_service.get_doctor_details(doc_query)
        if not doc_details:
            doc_record = find_doctor_by_name(doc_query)
            if doc_record:
                doc_details = provider_service.get_doctor_details(doc_record["id"])

        if not doc_details:
            doc_details = {
                "id": "doc-ravi",
                "name": "Dr. Ravi Kumar",
                "department": "General Medicine",
                "hospital": "Manipal Hospital",
                "locality": "Old Airport Road",
                "address": "98 HAL Old Airport Road, Kodihalli, Bengaluru",
                "consultationFee": "₹700",
                "consultationType": "In-Person & Teleconsultation",
                "experience": "12+ yrs experience",
                "rating": 4.9,
                "bio": "Senior Consultant Physician specializing in general diagnostics, internal medicine, and preventive healthcare.",
            }

        primary_action = "SHOW_DOCTOR_DETAILS"
        primary_data = {"doctor": doc_details}

    # --------------------------------------------------------------------------
    # 5. Nearby Doctors Inquiry ("Show doctors near Koramangala", "near me")
    # --------------------------------------------------------------------------
    elif (
        intent == "SEARCH_NEARBY"
        or any(a.get("action") == "SHOW_NEARBY_DOCTORS" or a.get("type") == "SHOW_NEARBY_DOCTORS" for a in raw_actions)
        or any(k in user_msg for k in ["near ", "nearby", "closest", "around "])
    ):
        primary_action = "SHOW_NEARBY_DOCTORS"
        nearby_action = next(
            (a for a in raw_actions if a.get("action") == "SHOW_NEARBY_DOCTORS" or a.get("type") == "SHOW_NEARBY_DOCTORS"),
            None
        )
        if nearby_action:
            p = nearby_action.get("payload") or nearby_action.get("data") or {}
            primary_data = p
        else:
            loc = parsed.get("location") or "Koramangala, Bengaluru"
            loc_clean = loc.replace(", Bengaluru", "").strip()
            docs = provider_service.search_by_location(locality=loc_clean, department=dept)
            if not docs:
                docs = provider_service.search_doctors(department=dept)
            primary_data = {
                "location": loc if "Bengaluru" in loc else f"{loc}, Bengaluru",
                "doctors": docs[:4],
            }

    # --------------------------------------------------------------------------
    # 6. Doctor Search / Directory ("Show doctors", "Find a general physician")
    # --------------------------------------------------------------------------
    elif (
        intent == "SEARCH_DOCTOR"
        or any(k in user_msg for k in ["show doctors", "find doctors", "list doctors", "physicians in", "specialist in"])
        or (any(a.get("action") == "SHOW_DOCTORS" or a.get("type") == "SHOW_DOCTORS" for a in raw_actions) and not symptoms)
    ):
        primary_action = "SHOW_DOCTORS"
        docs_found = provider_service.search_by_department(department=dept)
        if not docs_found:
            docs_found = provider_service.search_doctors()
        primary_data = {
            "department": dept,
            "doctors": docs_found,
            "dataSource": "Bengaluru Health Grid (Verified Provider)",
        }

    # --------------------------------------------------------------------------
    # 7. Department Suggestion Inquiry ("Which department should I visit?")
    # --------------------------------------------------------------------------
    elif (
        any(k in user_msg for k in ["which department", "what department", "what specialist", "recommend department", "suggest department"])
        or (not symptoms and any(k in user_msg for k in ["department", "specialist"]))
    ):
        primary_action = "SHOW_DEPARTMENT"
        primary_data = {
            "department": dept,
            "reason": dept_reason,
        }

    # --------------------------------------------------------------------------
    # 8. Patient Info Inquiry ("Show my patient info", "my profile")
    # --------------------------------------------------------------------------
    elif (
        intent == "UPDATE_PATIENT"
        or any(a.get("action") == "UPDATE_PATIENT" or a.get("type") == "UPDATE_PATIENT" for a in raw_actions)
        or any(k in user_msg for k in ["patient info", "my profile", "my details", "change my name", "my phone"])
    ):
        primary_action = "SHOW_PATIENT_INFO"
        p_info = get_patient_info(session_id)
        primary_data = {
            "patient": {
                "name": p_info.get("name", "Sarah Connor"),
                "age": p_info.get("age", 32),
                "phone": p_info.get("phone", "+91 98765 43210"),
                "preferredDepartment": p_info.get("preferred_department", dept),
            }
        }

    # --------------------------------------------------------------------------
    # 9. Clinical Symptoms Shared ("I have fever and headache for two days")
    # --------------------------------------------------------------------------
    elif symptoms:
        primary_action = "SHOW_SYMPTOMS"
        primary_data = {
            "symptoms": [
                {
                    "name": s.get("name") or s.get("symptom", "Symptom"),
                    "duration": s.get("duration") or "Recently reported",
                }
                for s in symptoms
            ]
        }

    # --------------------------------------------------------------------------
    # 10. Fallback: Welcome Component
    # --------------------------------------------------------------------------
    else:
        primary_action = "SHOW_WELCOME"
        primary_data = {
            "welcomeMessage": "Welcome to your AI Health Checkup & Appointment Coordinator.",
        }

    action_item = create_ui_action(primary_action, primary_data)
    structured_actions = [action_item] if action_item else []

    return {
        **state,
        "actions": structured_actions,
        "primary_ui_action": primary_action,
        "primary_ui_data": primary_data,
    }
