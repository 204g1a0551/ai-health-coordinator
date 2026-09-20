import re
from typing import List, Optional, Dict, Any
from app.agents.state import AgentState, SymptomItem, AgentAction

# Standard dictionary mapping common symptom phrases to canonical symptom names
SYMPTOM_PATTERNS = [
    (r"\b(high\s+)?fever(ish)?\b|\bhigh\s+temperature\b|\bpyrexia\b", "Fever"),
    (r"\bheadache(s)?\b|\bhead\s+ache\b|\bhead\s+pain\b", "Headache"),
    (r"\b(persistent\s+|dry\s+|wet\s+)?cough(ing)?\b", "Cough"),
    (r"\bsore\s+throat\b|\bthroat\s+pain\b|\bthroat\s+irritation\b", "Sore Throat"),
    (r"\bfatigue\b|\btiredness\b|\bexhaustion\b|\blethargy\b", "Fatigue"),
    (r"\bbody\s+ache(s)?\b|\bbody\s+pain\b", "Body Ache"),
    (r"\bchest\s+pain\b|\bchest\s+tightness\b", "Chest Pain"),
    (r"\bshortness\s+of\s+breath\b|\bdifficulty\s+breathing\b|\bbreathless(ness)?\b", "Shortness of Breath"),
    (r"\bnausea\b|\bfeeling\s+sick\b|\bqueasy\b", "Nausea"),
    (r"\bvomit(ing)?\b|\bpuk(ing)?\b", "Vomiting"),
    (r"\bdizziness\b|\blightheaded(ness)?\b|\bdizzy\b", "Dizziness"),
    (r"\bchills\b|\bshivering\b", "Chills"),
    (r"\brunny\s+nose\b|\bblocked\s+nose\b|\bnasal\s+congestion\b|\bcoryza\b", "Runny Nose"),
    (r"\bstomach\s+ache\b|\babdominal\s+pain\b|\bbelly\s+ache\b|\bstomach\s+pain\b", "Stomach Ache"),
    (r"\bdiarrhea\b|\bloose\s+stools\b|\bloose\s+motion\b", "Diarrhea"),
    (r"\brash\b|\bskin\s+rash\b|\bitching\b", "Rash"),
    (r"\bmuscle\s+pain\b|\bjoint\s+pain\b|\bmyalgia\b|\barthralgia\b", "Joint Pain"),
    (r"\bback\s+pain\b|\bbackache\b", "Back Pain"),
]

# Words to numbers for duration normalization
WORD_TO_NUM = {
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "a": "1",
    "couple": "2",
    "few": "3",
}


def extract_duration(text: str) -> Optional[str]:
    """
    Extract duration if explicitly mentioned in text (e.g. 'for two days', '2 days', 'since yesterday').
    Does not invent durations.
    """
    text_lower = text.lower()

    # Pattern for phrases like "for two days", "past 3 weeks", "last 2 days", "for a couple of days"
    dur_pattern = r"(?:for|past|last|since)?\s*(\b\w+\b)\s*(days?|hours?|weeks?|months?)\b"
    match = re.search(dur_pattern, text_lower)
    if match:
        num_word = match.group(1).strip()
        unit = match.group(2).strip()

        # Check if the preceding word is a number or word-number
        if num_word.isdigit():
            return f"{num_word} {unit}"
        elif num_word in WORD_TO_NUM:
            num = WORD_TO_NUM[num_word]
            unit_normalized = unit if num != "1" else unit.rstrip("s")
            return f"{num} {unit_normalized}"

    # Pattern for direct "X days/weeks/hours"
    direct_match = re.search(r"\b(\d+)\s*(days?|hours?|weeks?|months?)\b", text_lower)
    if direct_match:
        return f"{direct_match.group(1)} {direct_match.group(2)}"

    if "since yesterday" in text_lower:
        return "1 day"
    if "today" in text_lower or "since morning" in text_lower:
        return "Today"

    return None


def extract_symptoms(text: str) -> List[SymptomItem]:
    """
    Extract explicitly mentioned symptoms and their associated duration from text.
    Strictly avoids disease diagnosis and does not invent symptoms.
    """
    text_lower = text.lower()
    detected_symptoms: List[str] = []

    # Detect symptoms
    for pattern, canonical_name in SYMPTOM_PATTERNS:
        if re.search(pattern, text_lower):
            if canonical_name not in detected_symptoms:
                detected_symptoms.append(canonical_name)

    global_duration = extract_duration(text)

    results: List[SymptomItem] = []
    for sym_name in detected_symptoms:
        results.append({
            "name": sym_name,
            "duration": global_duration,
        })

    return results


def symptom_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Symptom Agent
    Extracts symptoms and duration, formats structured data, and prepares UI action.
    """
    user_msg = state.get("user_message", "")
    extracted = extract_symptoms(user_msg)

    # Return updated state
    actions = list(state.get("actions", []))
    if extracted:
        actions.append({
            "type": "UPDATE_SYMPTOMS",
            "payload": {
                "symptoms": extracted
            }
        })

    return {
        **state,
        "symptoms": extracted,
        "actions": actions,
    }
