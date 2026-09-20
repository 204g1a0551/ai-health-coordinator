import re
from typing import Dict, Any, List, Optional
from app.agents.state import AgentState
from app.services.medical_triage_engine import medical_triage_engine

# Department routing rules mapping keywords & symptoms to appropriate departments
DEPARTMENT_RULES = [
    (
        "Hematology",
        [
            r"\bplatelet(s)?\b", r"\bthrombocytopen(ia|ic)\b", r"\bplatelet\s+count\b",
            r"\banemia\b", r"\blow\s+hemoglobin\b", r"\bpurpura\b", r"\bpetechiae\b",
            r"\bblood\s+clot(ting)?\b", r"\bleukemia\b", r"\bhematolog(y|ist)\b", r"\bcbc\s+report\b"
        ],
        "The user’s request can be routed to Hematology for evaluation of platelet counts and blood disorders."
    ),
    (
        "Endocrinology",
        [
            r"\bdiabet(es|ic)\b", r"\bblood\s+sugar\b", r"\bhba1c\b", r"\bthyroid\b",
            r"\btsh\b", r"\bhypothyroid(ism)?\b", r"\bhyperthyroid(ism)?\b", r"\bendocrinolog(y|ist)\b"
        ],
        "The user’s request can be routed to Endocrinology for diabetes, thyroid, and metabolic evaluation."
    ),
    (
        "Nephrology",
        [
            r"\bcreatinine\b", r"\bkidney(s)?\b", r"\bkidney\s+stone(s)?\b", r"\bflank\s+pain\b",
            r"\bnephrolog(y|ist)\b", r"\bdialysis\b", r"\bhematuria\b", r"\bproteinuria\b", r"\burine\s+infection\b"
        ],
        "The user’s request can be routed to Nephrology for kidney and renal function evaluation."
    ),
    (
        "Cardiology",
        [
            r"\bheart\s*attack\b", r"\bcardiac\b", r"\bchest\s+pain\b", r"\bchest\s+tightness\b",
            r"\bchest\s+pressure\b", r"\bangina\b", r"\bpalpitation(s)?\b", r"\bheart\s+beat\b",
            r"\bhypertension\b", r"\bhigh\s+bp\b", r"\bcardiolog(y|ist)\b", r"\bheart\b", r"\becg\b"
        ],
        "The user’s request can be routed to Cardiology for cardiovascular and heart health evaluation."
    ),
    (
        "Pulmonology",
        [
            r"\basthma\b", r"\bwheez(ing)?\b", r"\bshortness\s+of\s+breath\b", r"\bbreathless(ness)?\b",
            r"\bdifficulty\s+breathing\b", r"\bbronchitis\b", r"\bpneumonia\b", r"\bpulmonolog(y|ist)\b", r"\blung(s)?\b"
        ],
        "The user’s request can be routed to Pulmonology for respiratory and lung health evaluation."
    ),
    (
        "Gastroenterology",
        [
            r"\bstomach\s+pain\b", r"\bstomach\s+ache\b", r"\babdominal\s+pain\b", r"\bbelly\s+pain\b",
            r"\bacid\s+reflux\b", r"\bheartburn\b", r"\bgerd\b", r"\bgastric\b", r"\bgastritis\b",
            r"\bbloat(ing)?\b", r"\bindigestion\b", r"\bulcer\b", r"\bdiarrhea\b", r"\bconstipation\b",
            r"\bgastroenterolog(y|ist)\b"
        ],
        "The user’s request can be routed to Gastroenterology for digestive health evaluation."
    ),
    (
        "Neurology",
        [
            r"\bmigraine\b", r"\bseizure(s)?\b", r"\bepilepsy\b", r"\bnumbness\b", r"\btremor(s)?\b",
            r"\bvertigo\b", r"\bparalysis\b", r"\bstroke\b", r"\bneurolog(y|ist)\b", r"\bnerve\s+pain\b"
        ],
        "The user’s request can be routed to Neurology for nervous system evaluation."
    ),
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
        "Gynecology",
        [
            r"\bpregnan(t|cy)\b", r"\bmenstrual\b", r"\bperiod\s+pain\b", r"\bcramps\b",
            r"\bpcos\b", r"\bpcod\b", r"\bgynecolog(y|ist)\b", r"\bovary\b", r"\bmaternity\b"
        ],
        "The user’s request can be routed to Gynecology & Obstetrics consultation."
    ),
    (
        "Psychiatry",
        [
            r"\bdepress(ion|ed)?\b", r"\banxiety\b", r"\bpanic\s+attack\b", r"\binsomnia\b",
            r"\bmental\s+health\b", r"\bpsychiatr(y|ist)\b", r"\bstress\b"
        ],
        "The user’s request can be routed to Psychiatry & Mental Health consultation."
    ),
    (
        "General Medicine",
        [
            r"\bfever\b", r"\bheadache\b", r"\bcough\b", r"\bfatigue\b", r"\bbody\s+ache\b",
            r"\bchills\b", r"\bnausea\b", r"\bvomiting\b", r"\bdizziness\b",
            r"\bgeneral\s+medicine\b", r"\binternal\s+medicine\b", r"\bphysician\b", r"\bcheckup\b"
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

    # 1. Primary check: Medical Big Data Triage Engine (multi-symptom & multi-specialty awareness)
    triage_pred = medical_triage_engine.predict(combined_text)
    if triage_pred.get("isMultiSpecialty"):
        matched_depts = triage_pred.get("matchedDepartments", [])
        dept_names = [d["department"] for d in matched_depts]
        return {
            "department": triage_pred["department"],
            "reason": f"Identified symptoms spanning {len(dept_names)} specialties: {', '.join(dept_names)}.",
            "is_multi_specialty": True,
            "multi_departments": matched_depts,
        }

    if triage_pred.get("department") and triage_pred["department"] != "General Medicine":
        return {
            "department": triage_pred["department"],
            "reason": f"Routed consultation based on clinical symptoms for {triage_pred['department']}.",
            "is_multi_specialty": False,
            "multi_departments": triage_pred.get("matchedDepartments", []),
        }

    # 2. Match against explicit department rules
    for dept_name, patterns, reason in DEPARTMENT_RULES:
        for pattern in patterns:
            if re.search(pattern, combined_text):
                return {
                    "department": dept_name,
                    "reason": reason,
                    "is_multi_specialty": False,
                    "multi_departments": [{"department": dept_name, "matchedKeyword": pattern}],
                }

    # If no specific patterns matched
    return {
        "department": "Needs clarification",
        "reason": "Please provide more details about your symptoms or the type of consultation you need.",
        "is_multi_specialty": False,
        "multi_departments": [],
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
    multi_depts = dept_result.get("multi_departments", [])

    actions = list(state.get("actions", []))

    # Only emit update action if a valid department is determined
    if dept_name != "Needs clarification":
        actions.append({
            "type": "UPDATE_DEPARTMENT",
            "payload": {
                "department": dept_name,
                "reason": dept_reason,
                "multi_departments": multi_depts,
            }
        })

    return {
        **state,
        "suggested_department": dept_name,
        "department_reason": dept_reason,
        "multi_departments": multi_depts,
        "actions": actions,
    }
