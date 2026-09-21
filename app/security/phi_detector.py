"""
Deterministic PII/PHI Detector for the Data Anonymization Privacy Gateway.
Utilizes precise regex patterns, boundary heuristics, and catalog matching
to identify sensitive identifiers without relying solely on an external LLM.
"""

import re
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel


class DetectedEntity(BaseModel):
    entity_type: str
    text: str
    surrogate_key: str
    start: int
    end: int
    confidence: float = 1.0


# ── Deterministic Regular Expressions ──────────────────────────────────────────

# Email: standard RFC 5322
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# Phone: Indian (+91 10-digit series starting 6-9) & International phone formats
PHONE_REGEX = re.compile(
    r"(?:\+91[\s-]?)?[6-9]\d{9}|\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
)

# National IDs (India: 14-digit ABHA, 12-digit Aadhaar)
ABHA_REGEX = re.compile(
    r"\b\d{2}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"
)
AADHAAR_REGEX = re.compile(
    r"\b\d{4}\s\d{4}\s\d{4}\b|\b[2-9]\d{11}\b"
)

# Patient Identifiers & Medical Record Numbers (MRN, UHID, PID, Patient ID)
PATIENT_ID_REGEX = re.compile(
    r"\b(?:Patient\s*ID|PID|MRN|UHID|PATIENT_ID|Hospital\s*No|Reg\s*No|Record\s*#?)\s*[:=\-#]?\s*([A-Za-z0-9\-_]{4,20})\b",
    re.I
)
STANDALONE_PID_REGEX = re.compile(
    r"\b(?:P|PID|MRN|UHID)[-_]?[0-9]{4,10}\b",
    re.I
)

# Insurance & Policy Numbers
INSURANCE_ID_REGEX = re.compile(
    r"\b(?:Policy\s*(?:No|Number|#)|Insurance\s*ID|Member\s*ID|Group\s*#?)\s*[:=\-#]?\s*([A-Za-z0-9\-_/]{4,25})\b",
    re.I
)
STANDALONE_INS_REGEX = re.compile(
    r"\b(?:POL|INS|GRP)[-_][A-Za-z0-9]{5,15}\b",
    re.I
)

# Prescription & Rx Identifiers
RX_ID_REGEX = re.compile(
    r"\b(?:Prescription\s*(?:No|#|ID)|Rx\s*(?:No|#|ID))\s*[:=\-#]?\s*([A-Za-z0-9\-_]{4,20})\b",
    re.I
)
STANDALONE_RX_REGEX = re.compile(
    r"\bRX[-_#]?[0-9]{4,12}\b",
    re.I
)

# Date of Birth (DOB) and Age
DOB_REGEX = re.compile(
    r"\b(?:DOB|Date\s*of\s*Birth|Birth\s*Date)\s*[:=\-]?\s*(\d{1,2}[-/.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2})[-/.]\d{2,4})\b",
    re.I
)
AGE_REGEX = re.compile(
    r"\b(?:Age)\s*[:=\-]?\s*(\d{1,3})\s*(?:years?|yrs?|yo)?\b",
    re.I
)

# Structured Patient / Doctor Name headers
STRUCTURED_PATIENT_NAME_REGEX = re.compile(
    r"\b(?:Patient(?:\s*Name)?|Pt\s*Name|Patient\s*:\s*Name)\s*[:=\-]\s*([A-Za-z][A-Za-z\s\.\']{2,35})\b",
    re.I
)
STRUCTURED_DOCTOR_NAME_REGEX = re.compile(
    r"\b(?:Doctor(?:\s*Name)?|Consultant|Physician|Attending)\s*[:=\-]\s*(?:Dr\.?\s*)?([A-Za-z][A-Za-z\s\.\']{2,35})\b",
    re.I
)
HONORIFIC_DOCTOR_REGEX = re.compile(
    r"\bDr\.\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b"
)

# Address & Location: Pin Codes & structured address blocks
PINCODE_REGEX = re.compile(
    r"\b[1-9][0-9]{5}\b"
)
STRUCTURED_ADDRESS_REGEX = re.compile(
    r"\b(?:Address|Residence|Location)\s*[:=\-]\s*([^\n\r,]{4,60}(?:,\s*[^\n\r,]{2,40})*)",
    re.I
)

# Common clinical terms to NEVER accidentally mask as names or IDs
CLINICAL_SAFEGUARD_TERMS: Set[str] = {
    "fever", "cough", "cold", "headache", "chest pain", "diabetes", "hypertension",
    "asthma", "pneumonia", "paracetamol", "amoxicillin", "metformin", "atorvastatin",
    "ibuprofen", "aspirin", "omeprazole", "cetirizine", "vitamin", "calcium",
    "blood pressure", "heart rate", "glucose", "platelet", "hemoglobin", "wbc", "rbc",
    "available", "morning", "evening", "afternoon", "tomorrow", "today", "yesterday",
    "cardiology", "neurology", "orthopedics", "dermatology", "pediatrics", "general medicine"
}


class PHIDetector:
    """
    Scans clinical text and user messages for identifiable PII/PHI.
    Returns categorized DetectedEntity objects ready for surrogate substitution.
    """

    def detect(self, text: str, known_names: Optional[List[str]] = None) -> List[DetectedEntity]:
        if not text or not isinstance(text, str):
            return []

        entities: List[DetectedEntity] = []

        # 1. Known names check (e.g. current patient session full_name, doctor names)
        if known_names:
            for name in known_names:
                if name and len(name.strip()) >= 3:
                    clean_name = name.strip()
                    pattern = re.compile(r"\b" + re.escape(clean_name) + r"\b", re.I)
                    for m in pattern.finditer(text):
                        entities.append(DetectedEntity(
                            entity_type="PATIENT_NAME",
                            text=m.group(0),
                            surrogate_key="[PATIENT_NAME]",
                            start=m.start(),
                            end=m.end(),
                            confidence=0.98
                        ))

        # 2. Email detection
        for m in EMAIL_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="EMAIL",
                text=m.group(0),
                surrogate_key="[EMAIL]",
                start=m.start(),
                end=m.end(),
                confidence=1.0
            ))

        # 3. ABHA ID detection (14 digits)
        for m in ABHA_REGEX.finditer(text):
            clean_digits = re.sub(r"\D", "", m.group(0))
            if len(clean_digits) == 14:
                entities.append(DetectedEntity(
                    entity_type="ABHA_ID",
                    text=m.group(0),
                    surrogate_key="[ABHA_ID]",
                    start=m.start(),
                    end=m.end(),
                    confidence=1.0
                ))

        # 4. Aadhaar detection (12 digits)
        for m in AADHAAR_REGEX.finditer(text):
            clean_digits = re.sub(r"\D", "", m.group(0))
            if len(clean_digits) == 12:
                # avoid collision if already detected as ABHA substring
                entities.append(DetectedEntity(
                    entity_type="AADHAAR",
                    text=m.group(0),
                    surrogate_key="[AADHAAR]",
                    start=m.start(),
                    end=m.end(),
                    confidence=0.95
                ))

        # 5. Phone numbers
        for m in PHONE_REGEX.finditer(text):
            val = m.group(0)
            digits = re.sub(r"\D", "", val)
            if len(digits) >= 10:
                entities.append(DetectedEntity(
                    entity_type="PHONE",
                    text=val,
                    surrogate_key="[PHONE]",
                    start=m.start(),
                    end=m.end(),
                    confidence=0.95
                ))

        # 6. Structured Patient Name
        for m in STRUCTURED_PATIENT_NAME_REGEX.finditer(text):
            matched_name = m.group(1).strip()
            # Verify not clinical safeguard word
            if matched_name.lower() not in CLINICAL_SAFEGUARD_TERMS and len(matched_name) >= 3:
                entities.append(DetectedEntity(
                    entity_type="PATIENT_NAME",
                    text=matched_name,
                    surrogate_key="[PATIENT_NAME]",
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.95
                ))

        # 7. Doctor Name (Structured & Honorific Dr.)
        for m in STRUCTURED_DOCTOR_NAME_REGEX.finditer(text):
            matched_doc = m.group(1).strip()
            if matched_doc.lower() not in CLINICAL_SAFEGUARD_TERMS and len(matched_doc) >= 3:
                entities.append(DetectedEntity(
                    entity_type="DOCTOR_NAME",
                    text=matched_doc,
                    surrogate_key="[DOCTOR_NAME]",
                    start=m.start(1),
                    end=m.end(1),
                    confidence=0.95
                ))
        for m in HONORIFIC_DOCTOR_REGEX.finditer(text):
            full_doc = m.group(0).strip()
            entities.append(DetectedEntity(
                entity_type="DOCTOR_NAME",
                text=full_doc,
                surrogate_key="[DOCTOR_NAME]",
                start=m.start(),
                end=m.end(),
                confidence=0.95
            ))

        # 8. Patient ID / MRN / UHID
        for m in PATIENT_ID_REGEX.finditer(text):
            pid_val = m.group(1).strip()
            entities.append(DetectedEntity(
                entity_type="PATIENT_ID",
                text=pid_val,
                surrogate_key="[PATIENT_ID]",
                start=m.start(1),
                end=m.end(1),
                confidence=0.98
            ))
        for m in STANDALONE_PID_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="PATIENT_ID",
                text=m.group(0),
                surrogate_key="[PATIENT_ID]",
                start=m.start(),
                end=m.end(),
                confidence=0.90
            ))

        # 9. Insurance ID / Policy Number
        for m in INSURANCE_ID_REGEX.finditer(text):
            ins_val = m.group(1).strip()
            entities.append(DetectedEntity(
                entity_type="INSURANCE_ID",
                text=ins_val,
                surrogate_key="[INSURANCE_ID]",
                start=m.start(1),
                end=m.end(1),
                confidence=0.98
            ))
        for m in STANDALONE_INS_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="INSURANCE_ID",
                text=m.group(0),
                surrogate_key="[INSURANCE_ID]",
                start=m.start(),
                end=m.end(),
                confidence=0.90
            ))

        # 10. Prescription / Rx ID
        for m in RX_ID_REGEX.finditer(text):
            rx_val = m.group(1).strip()
            entities.append(DetectedEntity(
                entity_type="RX_ID",
                text=rx_val,
                surrogate_key="[RX_ID]",
                start=m.start(1),
                end=m.end(1),
                confidence=0.98
            ))
        for m in STANDALONE_RX_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="RX_ID",
                text=m.group(0),
                surrogate_key="[RX_ID]",
                start=m.start(),
                end=m.end(),
                confidence=0.90
            ))

        # 11. DOB & Age
        for m in DOB_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="DOB",
                text=m.group(1),
                surrogate_key="[DOB]",
                start=m.start(1),
                end=m.end(1),
                confidence=0.95
            ))
        for m in AGE_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="AGE",
                text=m.group(1),
                surrogate_key="[AGE]",
                start=m.start(1),
                end=m.end(1),
                confidence=0.90
            ))

        # 12. Address & Pincodes
        for m in STRUCTURED_ADDRESS_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="ADDRESS",
                text=m.group(1).strip(),
                surrogate_key="[ADDRESS]",
                start=m.start(1),
                end=m.end(1),
                confidence=0.90
            ))
        for m in PINCODE_REGEX.finditer(text):
            entities.append(DetectedEntity(
                entity_type="PINCODE",
                text=m.group(0),
                surrogate_key="[PINCODE]",
                start=m.start(),
                end=m.end(),
                confidence=0.85
            ))

        # Resolve overlapping spans: sort by start position ascending, length descending
        return self._resolve_overlaps(entities)

    def _resolve_overlaps(self, entities: List[DetectedEntity]) -> List[DetectedEntity]:
        if not entities:
            return []

        # Sort primarily by start pos ascending, then by span length descending
        sorted_entities = sorted(entities, key=lambda e: (e.start, -(e.end - e.start)))

        non_overlapping: List[DetectedEntity] = []
        last_end = -1

        for entity in sorted_entities:
            # If entity starts at or after the previous entity's end, accept it
            if entity.start >= last_end:
                non_overlapping.append(entity)
                last_end = entity.end

        return non_overlapping


phi_detector = PHIDetector()
