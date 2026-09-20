import re
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState, UIAction

# Predefined allowed controlled actions
ALLOWED_ACTIONS = {
    "UPDATE_SYMPTOMS",
    "UPDATE_DEPARTMENT",
    "SHOW_DOCTORS",
    "SHOW_SLOTS",
    "BOOK_APPOINTMENT",
    "CANCEL_APPOINTMENT",
    "UPDATE_PATIENT",
    "CLEAR_APPOINTMENT",
    "SHOW_NEARBY_DOCTORS",
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
        "payload": payload,
        "type": action_name,  # Alias for backward compatibility
    }


def ui_action_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: UI Agent / UI Action Layer
    Consolidates domain agent results into controlled, safe, structured UI actions.
    Guarantees:
    - Never generates arbitrary JS, HTML, CSS, or DOM commands.
    - Emits only predefined actions:
      UPDATE_SYMPTOMS, UPDATE_DEPARTMENT, SHOW_DOCTORS, SHOW_SLOTS,
      BOOK_APPOINTMENT, CANCEL_APPOINTMENT, UPDATE_PATIENT, CLEAR_APPOINTMENT.
    """
    raw_actions = state.get("actions", [])
    symptoms = state.get("symptoms", [])
    dept = state.get("suggested_department")
    dept_reason = state.get("department_reason")
    doctor_slot_results = state.get("doctor_slot_results")
    appointment_result = state.get("appointment_action_result")
    patient_info = state.get("patient_info")
    user_msg = state.get("user_message", "").lower()

    structured_actions: List[UIAction] = []
    seen_action_signatures = set()
    seen_action_types = set()

    def add_action(act_name: str, payload: Dict[str, Any]):
        if act_name in {"UPDATE_DEPARTMENT", "CLEAR_APPOINTMENT", "CANCEL_APPOINTMENT", "UPDATE_SYMPTOMS", "SHOW_DOCTORS", "SHOW_SLOTS", "BOOK_APPOINTMENT", "SHOW_NEARBY_DOCTORS", "REQUEST_LOCATION_PERMISSION"}:
            if act_name in seen_action_types:
                return
        sig = f"{act_name}:{str(payload)}"
        if sig in seen_action_signatures:
            return
        action_obj = create_ui_action(act_name, payload)
        if action_obj:
            structured_actions.append(action_obj)
            seen_action_signatures.add(sig)
            seen_action_types.add(act_name)

    # 1. Process Patient Info Updates
    # Check if patient info agent ran or if raw action contains UPDATE_PATIENT
    for raw in raw_actions:
        r_type = raw.get("type") or raw.get("action")
        if r_type == "UPDATE_PATIENT":
            data = raw.get("data") or raw.get("payload", {}).get("data") or raw.get("payload", {})
            if data:
                add_action("UPDATE_PATIENT", data)

    # 2. Process Symptoms
    if symptoms:
        add_action("UPDATE_SYMPTOMS", {"symptoms": symptoms})

    # 3. Process Suggested Department
    if dept and dept != "Needs clarification":
        add_action("UPDATE_DEPARTMENT", {
            "department": dept,
            "reason": dept_reason or f"Routed consultation for {dept}."
        })

    # 4. Process Doctors & Slots (e.g. "I want a general physician tomorrow evening.")
    # Converts into SHOW_DOCTORS and SHOW_SLOTS
    for raw in raw_actions:
        r_type = raw.get("type") or raw.get("action")
        if r_type == "UPDATE_DOCTORS_AND_SLOTS":
            p = raw.get("payload", {})
            if p.get("department"):
                add_action("UPDATE_DEPARTMENT", {
                    "department": p["department"],
                    "reason": f"Consultation search for {p['department']}."
                })
            if p.get("doctors"):
                add_action("SHOW_DOCTORS", {
                    "doctors": p["doctors"],
                    "department": p.get("department", dept),
                    "dataSource": p.get("dataSource", "Bengaluru Health Grid (Verified Provider)"),
                    "timestamp": p.get("timestamp"),
                })
            if p.get("slots"):
                add_action("SHOW_SLOTS", {
                    "slots": p["slots"],
                    "date": p.get("date", "Tomorrow"),
                    "dataSource": p.get("dataSource", "Bengaluru Health Grid (Verified Provider)"),
                    "timestamp": p.get("timestamp"),
                })
        elif r_type == "SHOW_SLOTS":
            p = raw.get("payload", {})
            add_action("SHOW_SLOTS", p)
        elif r_type == "SHOW_DOCTORS":
            p = raw.get("payload", {})
            add_action("SHOW_DOCTORS", p)

    # 5. Process Appointments (BOOK_APPOINTMENT, CANCEL_APPOINTMENT, CLEAR_APPOINTMENT)
    for raw in raw_actions:
        r_type = raw.get("type") or raw.get("action")
        if r_type == "BOOK_APPOINTMENT":
            p = raw.get("payload", {})
            appt = p.get("appointment") or p
            add_action("BOOK_APPOINTMENT", {"appointment": appt})
            if appt.get("department"):
                add_action("UPDATE_DEPARTMENT", {
                    "department": appt["department"],
                    "reason": f"Appointment booked with {appt.get('doctor', 'doctor')}."
                })
        elif r_type == "CANCEL_APPOINTMENT":
            add_action("CANCEL_APPOINTMENT", {"status": "Cancelled"})
        elif r_type == "CLEAR_APPOINTMENT":
            add_action("CLEAR_APPOINTMENT", {})

    # 6. Process Location Actions (SHOW_NEARBY_DOCTORS, REQUEST_LOCATION_PERMISSION)
    for raw in raw_actions:
        r_type = raw.get("type") or raw.get("action")
        if r_type == "SHOW_NEARBY_DOCTORS":
            p = raw.get("payload", {})
            add_action("SHOW_NEARBY_DOCTORS", p)
        elif r_type == "REQUEST_LOCATION_PERMISSION":
            p = raw.get("payload", {})
            add_action("REQUEST_LOCATION_PERMISSION", p)

    # Check for explicit clear appointment phrases
    if any(k in user_msg for k in ["clear appointment", "reset appointment", "clear summary"]):
        add_action("CLEAR_APPOINTMENT", {})

    return {
        **state,
        "actions": structured_actions,
    }
