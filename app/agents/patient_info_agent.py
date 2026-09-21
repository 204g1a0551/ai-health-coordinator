import re
from typing import Dict, Any, Optional
from app.agents.state import AgentState
from app.db.repository import get_patient_info, update_patient_info


VALID_DEPARTMENTS = [
    "General Medicine",
    "Dermatology",
    "ENT",
    "Orthopedics",
    "Pediatrics",
    "Ophthalmology",
    "Dental",
]


def extract_patient_updates(text: str) -> Dict[str, Any]:
    """
    Extracts basic demographic/contact demo info:
    - name
    - age
    - phone
    - preferred_department
    Strictly avoids storing sensitive medical records or diagnosis data.
    """
    updates: Dict[str, Any] = {}
    cleaned_text = text.strip()

    # 1. Extract Name
    # Matches: "set my name to Mahesh", "change name to Mahesh", "my name is Mahesh", "call me Mahesh"
    name_match = re.search(
        r"(?:(?:set|change|update)\s+(?:my\s+)?name\s+to|my\s+name\s+is|call\s+me)\s+([A-Za-z\s'\-]+)",
        cleaned_text,
        re.IGNORECASE,
    )
    if name_match:
        candidate_name = name_match.group(1).strip()
        # Strip trailing punctuation or words like "please", "thanks"
        candidate_name = re.sub(r"[.,!?;]+$", "", candidate_name).strip()
        candidate_name = re.sub(r"\b(please|thanks|thank you)\b.*$", "", candidate_name, flags=re.IGNORECASE).strip()
        if candidate_name and len(candidate_name) <= 50:
            updates["name"] = candidate_name.title()

    # 2. Extract Phone
    # Matches: "change my phone number to 555-1234", "phone is 9876543210", "set phone to +1 555..."
    phone_match = re.search(
        r"(?:(?:phone|number|mobile|contact)\s*(?:is|to|number\s+to)?\s*[:=]?\s*)([\+\d\s\-\(\)\.]{7,20})",
        cleaned_text,
        re.IGNORECASE,
    )
    if phone_match:
        raw_phone = phone_match.group(1).strip()
        # Clean trailing punctuation
        raw_phone = re.sub(r"[.,!?;]+$", "", raw_phone).strip()
        # Verify it has at least 5 digits
        if len(re.findall(r"\d", raw_phone)) >= 5:
            updates["phone"] = raw_phone
    elif re.search(r"\bphone\b", cleaned_text, re.IGNORECASE):
        # Look for a standalone phone pattern in the message if the word phone is present
        direct_digits = re.search(r"(\+?[\d\s\-\(\)\.]{7,20})", cleaned_text)
        if direct_digits:
            raw_phone = direct_digits.group(1).strip()
            raw_phone = re.sub(r"[.,!?;]+$", "", raw_phone).strip()
            if len(re.findall(r"\d", raw_phone)) >= 7:
                updates["phone"] = raw_phone

    # 3. Extract Age
    # Matches: "set my age to 28", "change my age to 35", "my age is 28", "i am 28 years old", "i'm 28"
    age_match = re.search(
        r"(?:(?:set|change|update)\s+(?:my\s+)?age\s+to|my\s+age\s+is|(?:i\s+am|i'm))\s+(\d{1,3})(?:\s*(?:years?\s*old|yrs?\s*old)?)?",
        cleaned_text,
        re.IGNORECASE,
    )
    if age_match:
        try:
            parsed_age = int(age_match.group(1))
            if 0 < parsed_age < 125:
                updates["age"] = parsed_age
        except ValueError:
            pass

    # 4. Extract Preferred Department
    dept_match = re.search(
        r"(?:preferred\s+department\s+(?:is|to)|department\s+to)\s+([A-Za-z\s]+)",
        cleaned_text,
        re.IGNORECASE,
    )
    if dept_match:
        raw_dept = dept_match.group(1).strip()
        raw_dept = re.sub(r"[.,!?;]+$", "", raw_dept).strip()
        for dept in VALID_DEPARTMENTS:
            if dept.lower() in raw_dept.lower() or raw_dept.lower() in dept.lower():
                updates["preferred_department"] = dept
                break
    else:
        # Check if user mentioned preferred department along with one of the valid department names
        if "preferred" in cleaned_text.lower() or "department" in cleaned_text.lower():
            for dept in VALID_DEPARTMENTS:
                if dept.lower() in cleaned_text.lower():
                    updates["preferred_department"] = dept
                    break

    return updates


def patient_info_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Patient Info Agent
    Manages basic demo demographic and contact information:
    - Name
    - Age
    - Phone
    - Preferred department
    Protects user privacy: strictly avoids storing sensitive medical diagnoses or records.
    Returns structured UI action for Angular Dashboard.
    """
    user_msg = state.get("user_message", "").strip()
    session_id = state.get("session_id", "default-session")
    lower_msg = user_msg.lower()

    actions = list(state.get("actions", []))
    updates = extract_patient_updates(user_msg)

    # Check for "show" or "display" patient info request
    is_show_request = any(
        kw in lower_msg
        for kw in ["show", "view", "display", "check", "what is my", "my patient info", "my profile"]
    ) and not updates

    # Check if user requested changing phone without providing number
    wants_phone_change_only = (
        ("phone" in lower_msg or "number" in lower_msg)
        and any(w in lower_msg for w in ["change", "update", "set", "new"])
        and "phone" not in updates
    )

    if wants_phone_change_only:
        final_msg = (
            "Please provide the phone number you would like to set "
            "(for example: 'Change my phone number to +1 (555) 019-2834')."
        )
        return {
            **state,
            "final_response": final_msg,
        }

    if is_show_request:
        current_info = get_patient_info(session_id)
        dept_str = f"• Preferred Department: {current_info.get('preferred_department')}\n" if current_info.get("preferred_department") else ""
        final_msg = (
            f"Here is your current patient information:\n"
            f"• Patient Name: {current_info.get('name', 'Not provided')}\n"
            f"• Age: {current_info.get('age', '--')} yrs\n"
            f"• Phone: {current_info.get('phone', '--')}\n"
            f"{dept_str}"
            "You can update these details anytime by saying 'Set my name to...', 'Change my phone number to...', etc."
        )
        structured_action = {
            "type": "UPDATE_PATIENT",
            "action": "UPDATE_PATIENT",
            "data": current_info,
            "payload": {
                "action": "UPDATE_PATIENT",
                "data": current_info,
            },
        }
        actions.append(structured_action)
        return {
            **state,
            "patient_info": current_info,
            "actions": actions,
            "final_response": final_msg,
        }

    if updates:
        updated_info = update_patient_info(session_id, updates)

        # Build human-readable response confirmation
        confirmations = []
        if "name" in updates:
            confirmations.append(f"name to {updates['name']}")
        if "age" in updates:
            confirmations.append(f"age to {updates['age']} years")
        if "phone" in updates:
            confirmations.append(f"phone number to {updates['phone']}")
        if "preferred_department" in updates:
            confirmations.append(f"preferred department to {updates['preferred_department']}")

        changes_summary = " and ".join(confirmations)
        final_msg = f"Updated your {changes_summary}. Your patient profile has been updated on the dashboard."

        # Structured action for Angular
        structured_action = {
            "type": "UPDATE_PATIENT",
            "action": "UPDATE_PATIENT",
            "data": updates,
            "payload": {
                "action": "UPDATE_PATIENT",
                "data": updates,
            },
        }
        actions.append(structured_action)

        return {
            **state,
            "patient_info": updated_info,
            "actions": actions,
            "final_response": final_msg,
        }

    # Fallback if no specific fields were matched
    current_info = get_patient_info(session_id)
    final_msg = (
        "I can help update your patient information (Name, Age, Phone, or Preferred Department). "
        "For example, try saying: 'Set my name to Mahesh.' or 'Change my phone number to 555-0199.'"
    )
    return {
        **state,
        "patient_info": current_info,
        "final_response": final_msg,
    }
