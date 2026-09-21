"""
PHI/PII Sanitization, Redaction, and Masking module.
Aligned with ABDM (Ayushman Bharat Digital Mission) and DPDP Act 2023.
"""

import re
from typing import Dict, Any


# Regex patterns for sensitive identifiers
ABHA_PATTERN = re.compile(r"\b(\d{2})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b")
AADHAAR_PATTERN = re.compile(r"\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b")
PHONE_PATTERN = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}|\b\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")


def mask_abha_id(abha_str: str) -> str:
    """Masks 14-digit ABHA ID into XX-XXXX-XXXX-1234 format."""
    digits = re.sub(r"\D", "", abha_str)
    if len(digits) == 14:
        return f"{digits[:2]}-XXXX-XXXX-{digits[-4:]}"
    return "XX-XXXX-XXXX-" + abha_str[-4:] if len(abha_str) >= 4 else "XX-XXXX-XXXX-XXXX"


def mask_aadhaar(aadhaar_str: str) -> str:
    """Masks 12-digit Aadhaar into XXXXXXXX1234 format."""
    digits = re.sub(r"\D", "", aadhaar_str)
    if len(digits) == 12:
        return f"XXXXXXXX{digits[-4:]}"
    return "XXXXXXXX" + aadhaar_str[-4:] if len(aadhaar_str) >= 4 else "XXXXXXXXXXXX"


def mask_phone(phone_str: str) -> str:
    """Masks phone number to retain only country prefix and last 4 digits."""
    clean = phone_str.strip()
    if len(clean) <= 4:
        return "****"
    return f"{clean[:3]}*****{clean[-4:]}"


def mask_email(email_str: str) -> str:
    """Masks email address into j***e@domain.com format."""
    try:
        user_part, domain_part = email_str.split("@", 1)
        if len(user_part) <= 2:
            masked_user = f"{user_part[0]}***"
        else:
            masked_user = f"{user_part[0]}***{user_part[-1]}"
        return f"{masked_user}@{domain_part}"
    except Exception:
        return "***@masked.domain"


def sanitize_phi_for_llm(text: str) -> str:
    """
    Sanitizes raw clinical or user text before sending to LLMs/agentic context,
    enforcing minimum-necessary data exposure.
    """
    if not text or not isinstance(text, str):
        return text

    sanitized = text

    # Redact Credit Cards
    sanitized = CARD_PATTERN.sub("[CARD_REDACTED]", sanitized)

    # Mask ABHA IDs
    def replace_abha(match):
        d1, d2, d3, d4 = match.groups()
        return f"{d1}-XXXX-XXXX-{d4}"
    sanitized = ABHA_PATTERN.sub(replace_abha, sanitized)

    # Mask Aadhaar
    def replace_aadhaar(match):
        d1, d2, d3 = match.groups()
        return f"XXXXXXXX{d3}"
    sanitized = AADHAAR_PATTERN.sub(replace_aadhaar, sanitized)

    # Redact Email
    def replace_email(match):
        return mask_email(match.group(0))
    sanitized = EMAIL_PATTERN.sub(replace_email, sanitized)

    # Mask Phones
    def replace_phone(match):
        raw = match.group(0)
        digits = re.sub(r"\D", "", raw)
        last4 = digits[-4:] if len(digits) >= 4 else "XXXX"
        return f"[PHONE: ...{last4}]"
    sanitized = PHONE_PATTERN.sub(replace_phone, sanitized)

    return sanitized


def sanitize_dict_phi(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively traverses dictionary and masks identifiable keys."""
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for k, v in data.items():
        k_lower = k.lower()
        if isinstance(v, str):
            if "phone" in k_lower:
                sanitized[k] = mask_phone(v)
            elif "abha" in k_lower:
                sanitized[k] = mask_abha_id(v)
            elif "aadhaar" in k_lower:
                sanitized[k] = mask_aadhaar(v)
            elif "email" in k_lower:
                sanitized[k] = mask_email(v)
            elif "password" in k_lower or "secret" in k_lower:
                sanitized[k] = "[PROTECTED]"
            else:
                sanitized[k] = sanitize_phi_for_llm(v)
        elif isinstance(v, dict):
            sanitized[k] = sanitize_dict_phi(v)
        elif isinstance(v, list):
            sanitized[k] = [sanitize_dict_phi(x) if isinstance(x, dict) else x for x in v]
        else:
            sanitized[k] = v
    return sanitized
