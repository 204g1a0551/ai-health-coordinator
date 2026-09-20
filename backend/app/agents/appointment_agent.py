import re
from typing import Dict, Any, Optional
from app.agents.state import AgentState
from app.db.repository import (
    book_appointment,
    cancel_appointment,
    get_active_appointment,
    find_doctor_by_name,
)


def extract_booking_entities(text: str):
    """
    Extract doctor name, date, and time slot from phrases such as:
    'Book Dr. Ravi tomorrow at 6 PM' or 'Book appointment with Dr. Priya tomorrow 6:00 PM'
    """
    stop_words = {"tomorrow", "today", "at", "on", "for", "in", "this", "next", "morning", "evening", "afternoon"}
    doc_match = re.search(r"\b(?:dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", text, re.IGNORECASE)
    doctor_query = "Dr. Ravi Kumar"
    if doc_match:
        words = doc_match.group(0).split()
        cleaned_words = [w for w in words if w.lower() not in stop_words]
        doctor_query = " ".join(cleaned_words)

    # 2. Time extraction
    time_match = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM))\b", text)
    if time_match:
        time_query = time_match.group(1).strip()
    else:
        # Check for 24h format e.g. 18:00
        time_24 = re.search(r"\b(\d{1,2}:\d{2})\b", text)
        time_query = time_24.group(1).strip() if time_24 else "6:00 PM"

    # 3. Date extraction
    date_query = "tomorrow"
    if "today" in text.lower():
        date_query = "today"

    return doctor_query, date_query, time_query


def appointment_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Appointment Agent
    Handles booking, cancellation, rescheduling, and status inquiry.
    Validates availability, updates database, and returns structured results.
    """
    user_msg = state.get("user_message", "").strip()
    session_id = state.get("session_id", "default-session")
    lower_msg = user_msg.lower()

    actions = list(state.get("actions", []))

    # Case 1: Cancel appointment
    if any(k in lower_msg for k in ["cancel", "delete", "drop appointment"]):
        cancel_res = cancel_appointment(session_id)
        if cancel_res.get("success"):
            actions.append({
                "type": "CANCEL_APPOINTMENT",
                "payload": {"status": "Cancelled"}
            })
            appointment_info = {
                "action": "CANCEL_APPOINTMENT",
                "status": "Cancelled"
            }
            final_msg = "Your appointment has been successfully cancelled. The reserved slot has been freed."
        else:
            appointment_info = {"action": "CANCEL_APPOINTMENT", "status": "Failed"}
            final_msg = cancel_res.get("error", "No active appointment found to cancel.")

        return {
            **state,
            "appointment_action_result": appointment_info,
            "actions": actions,
            "final_response": final_msg,
        }

    # Case 2: Show / Details
    if any(k in lower_msg for k in ["show appointment", "my appointment", "appointment details", "status"]):
        active = get_active_appointment(session_id)
        if active:
            appointment_info = {
                "action": "SHOW_APPOINTMENT",
                "appointment": active
            }
            final_msg = (
                f"You have a confirmed appointment with {active['doctor']} ({active['department']}) "
                f"on {active['displayDate']} at {active['time']}."
            )
        else:
            appointment_info = {"action": "SHOW_APPOINTMENT", "appointment": None}
            final_msg = "You currently have no active appointment booked."

        return {
            **state,
            "appointment_action_result": appointment_info,
            "actions": actions,
            "final_response": final_msg,
        }

    # Case 3: Book / Reschedule Appointment
    doctor_query, date_query, time_query = extract_booking_entities(user_msg)

    booking_res = book_appointment(session_id, doctor_query, time_query, date_query)

    if booking_res.get("success"):
        appt_data = booking_res["appointment"]
        structured_res = {
            "action": "BOOK_APPOINTMENT",
            "appointment": {
                "doctor": appt_data["doctor"],
                "department": appt_data["department"],
                "date": appt_data["date"],
                "time": appt_data["time"],
                "status": appt_data["status"]
            }
        }

        # Structured action for Angular
        actions.append({
            "type": "BOOK_APPOINTMENT",
            "payload": structured_res
        })

        # Also update department if not yet set
        actions.append({
            "type": "UPDATE_DEPARTMENT",
            "payload": {
                "department": appt_data["department"],
                "reason": f"Appointment booked with {appt_data['doctor']}."
            }
        })

        final_msg = (
            f"Appointment Confirmed with {appt_data['doctor']} ({appt_data['department']}) "
            f"on {appt_data['displayDate']} at {appt_data['displayTime']}. "
            "Your appointment summary on the dashboard has been updated."
        )

        return {
            **state,
            "suggested_department": appt_data["department"],
            "appointment_action_result": structured_res,
            "actions": actions,
            "final_response": final_msg,
        }
    else:
        # Slot was unavailable or doctor not found
        error_msg = booking_res.get("error", "The requested time slot is unavailable.")
        alts = booking_res.get("alternatives", [])
        alt_text = f" Available alternatives for {booking_res.get('doctor', 'this doctor')}: {', '.join(alts)}." if alts else ""

        final_msg = f"{error_msg}{alt_text} Please select one of the available alternatives."
        structured_res = {
            "action": "BOOK_APPOINTMENT_FAILED",
            "error": error_msg,
            "alternatives": alts
        }

        return {
            **state,
            "appointment_action_result": structured_res,
            "actions": actions,
            "final_response": final_msg,
        }
