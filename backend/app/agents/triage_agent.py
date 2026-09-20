import re
from typing import Any, Dict, List

from app.agents.state import AgentState
from app.services.emergency_service import get_emergency_contacts


_CATEGORY_PATTERNS = {
    "chest_pain": (
        r"\b(?:severe|crushing|heavy|pressure|tight|squeezing)\s+"
        r"(?:chest|chest\s+pain)|\bchest\s+pain\b"
    ),
    "breathing_difficulty": (
        r"\b(?:severe\s+)?(?:difficulty|trouble|hard)\s+breathing\b|"
        r"\bstruggling\s+to\s+breathe\b|"
        r"\b(?:can'?t|cannot|unable\s+to)\s+breathe\b|\bgasping\b|\bblue\s+lips?\b"
    ),
    "stroke_signs": (
        r"\b(?:face\s+droop(?:ping|ing)?|facial\s+droop|"
        r"one\s+side\s+of\s+(?:my\s+)?face\s+is\s+drooping|"
        r"one\s+side\s+(?:weak|numb)|"
        r"arm\s+(?:weak|numb)|speech\s+(?:slurred|difficulty)|"
        r"cannot\s+(?:speak|lift\s+(?:my|one)\s+arm))\b"
    ),
    "uncontrolled_bleeding": (
        r"\b(?:severe|heavy|uncontrolled|won'?t\s+stop)\s+(?:bleeding|bleed)\b|"
        r"\bbleeding\s+(?:heavily|profusely|won'?t\s+stop)\b"
    ),
    "loss_of_consciousness": (
        r"\b(?:lost|loss\s+of|passed\s+out|fainted|unconscious|not\s+conscious)\b"
    ),
    "seizure": r"\b(?:seizure|convuls(?:ion|ing)|fitting)\b",
    "severe_allergic_reaction": (
        r"\b(?:anaphylaxis|anaphylactic|throat\s+(?:is\s+)?closing|"
        r"face\s+or\s+(?:lip|tongue)\s+swelling|severe\s+allergic)\b"
    ),
    "self_harm_danger": (
        r"\b(?:suicid(?:e|al)|kill\s+myself|end\s+my\s+life|"
        r"hurt\s+myself|self[-\s]?harm)\b"
    ),
}

_NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|without|never|denies?|don'?t|do\s+not|"
    r"doesn'?t|didn'?t)\b[^.!?]{0,35}$",
    re.IGNORECASE,
)


def _has_positive_match(message: str, pattern: str) -> bool:
    for match in re.finditer(pattern, message, re.IGNORECASE):
        context = message[max(0, match.start() - 30):match.start()]
        if not _NEGATION_PATTERN.search(context):
            return True
    return False


def detect_red_flags(message: str) -> List[str]:
    """Return conservative red-flag categories without attempting a diagnosis."""
    return [
        category
        for category, pattern in _CATEGORY_PATTERNS.items()
        if _has_positive_match(message, pattern)
    ]


def triage_node(state: AgentState) -> AgentState:
    matched_categories = detect_red_flags(state.get("user_message", ""))
    if not matched_categories:
        return {
            **state,
            "triage_status": "NORMAL",
            "normal_workflow_allowed": True,
            "triage_action": "CONTINUE_WORKFLOW",
        }

    country_region = state.get("country_region") or "IN"
    emergency_data = {
        "reason": "Potential emergency symptoms detected",
        "matched_categories": matched_categories,
        "contacts": get_emergency_contacts(country_region),
        "country_region": country_region,
        "location_options": {
            "permission_available": True,
            "manual_locality_supported": True,
        },
        "disclaimer": (
            "This application is not a substitute for emergency medical care."
        ),
    }
    emergency_actions = [
        {"action": "SHOW_EMERGENCY_ALERT", "data": emergency_data},
        {"action": "SHOW_EMERGENCY_CONTACTS", "data": emergency_data},
        {"action": "SHOW_EMERGENCY_DEPARTMENTS", "data": emergency_data},
        {"action": "BLOCK_NORMAL_WORKFLOW", "data": {"blocked": True}},
    ]
    return {
        **state,
        "triage_status": "EMERGENCY",
        "triage_reason": "Potential emergency symptoms detected",
        "triage_action": "EMERGENCY_WORKFLOW",
        "matched_categories": matched_categories,
        "normal_workflow_allowed": False,
        "route": "EMERGENCY_WORKFLOW",
        "actions": emergency_actions,
        "primary_ui_action": "SHOW_EMERGENCY_ALERT",
        "primary_ui_data": emergency_data,
        "final_response": (
            "This may be a medical emergency. Seek immediate emergency medical "
            "care now. Call your local emergency number or go to the nearest "
            "emergency department. Do not wait for this app."
        ),
    }


def route_after_triage(state: AgentState) -> str:
    return "emergency" if state.get("triage_status") == "EMERGENCY" else "continue"
