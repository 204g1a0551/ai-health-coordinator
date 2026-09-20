import re
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState

# Department routing rules mapping keywords & symptoms to appropriate departments
DEPARTMENT_RULES = [
    (
        "Dental",
        [r"\btooth\b", r"\bteeth\b", r"\btoothache\b", r"\bgum(s)?\b", r"\bcavity\b", r"\bdental\b", r"\bdentist\b"],
        "The user’s request can be routed to dental consultation for oral and dental evaluation."
    ),
    (
        "Ophthalmology",
        [r"\beye(s)?\b", r"\bvision\b", r"\bblurry\s+vision\b", r"\beye\s+pain\b", r"\bophthalmolog(y|ist)\b"],
        "The user’s request can be routed to ophthalmology for eye and vision evaluation."
    ),
    (
        "ENT",
        [
            r"\bsore\s+throat\b", r"\bthroat\b", r"\bear(s)?\b", r"\bearache\b", r"\bhearing\b",
            r"\brunny\s+nose\b", r"\bnasal\b", r"\bsinus(es)?\b", r"\bent\b"
        ],
        "The user’s request can be routed to ENT (Ear, Nose & Throat) consultation."
    ),
    (
        "Dermatology",
        [
            r"\brash\b", r"\bskin\b", r"\bitch(ing|y)?\b", r"\beczema\b", r"\bacne\b",
            r"\bhives\b", r"\bdermatolog(y|ist)\b"
        ],
        "The user’s request can be routed to dermatology consultation."
    ),
    (
        "Orthopedics",
        [
            r"\bback\s+pain\b", r"\bbackache\b", r"\bjoint\s+pain\b", r"\bknee\b",
            r"\bbone\b", r"\bfracture\b", r"\bsprain\b", r"\bshoulder\b", r"\borthopedic(s)?\b"
        ],
        "The user’s request can be routed to orthopedics consultation for musculoskeletal evaluation."
    ),
    (
        "Pediatrics",
        [
            r"\bbaby\b", r"\binfant\b", r"\btoddler\b", r"\bchild(ren)?\b", r"\bkid(s)?\b",
            r"\bpediatric(s|ian)?\b"
        ],
        "The user’s request can be routed to pediatrics for child care consultation."
    ),
    (
        "General Medicine",
        [
            r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bfatigue\b", r"\bbody\s+ache\b",
            r"\bchills\b", r"\bnausea\b", r"\bvomiting\b", r"\bdizziness\b", r"\bstomach\s+ache\b",
            r"\bgeneral\s+medicine\b", r"\binternal\s+medicine\b", r"\bphysician\b"
        ],
        "The user’s request can be routed to general medical consultation."
    ),
]


def determine_department(user_msg: str, symptoms: List[Dict[str, Optional[str]]]) -> Dict[str, str]:
    """
    Suggest an appropriate medical department based on extracted symptoms and request.
    Does NOT diagnose diseases.
    Does NOT claim medical necessity.
    Returns 'Needs clarification' if unclear.
    """
    # Combine text representation of symptoms and raw user message
    symptom_names = " ".join([s.get("name", "") for s in symptoms]).lower()
    combined_text = f"{user_msg.lower()} {symptom_names}".strip()

    if not combined_text:
        return {
            "department": "Needs clarification",
            "reason": "No symptoms or department preferences were specified."
        }

    # Match against department rules in priority order
    for dept_name, patterns, reason in DEPARTMENT_RULES:
        for pattern in patterns:
            if re.search(pattern, combined_text):
                return {
                    "department": dept_name,
                    "reason": reason
                }

    # If no specific patterns matched
    return {
        "department": "Needs clarification",
        "reason": "Please provide more details about your symptoms or the type of consultation you need."
    }


def department_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Department Agent
    Suggests department, avoids disease diagnosis, and prepares UPDATE_DEPARTMENT action.
    """
    user_msg = state.get("user_message", "")
    symptoms = state.get("symptoms", [])

    dept_result = determine_department(user_msg, symptoms)
    dept_name = dept_result["department"]
    dept_reason = dept_result["reason"]

    actions = list(state.get("actions", []))

    # Only emit update action if a valid department is determined
    if dept_name != "Needs clarification":
        actions.append({
            "type": "UPDATE_DEPARTMENT",
            "payload": {
                "department": dept_name,
                "reason": dept_reason
            }
        })

    return {
        **state,
        "suggested_department": dept_name,
        "department_reason": dept_reason,
        "actions": actions,
    }
