import os
from typing import Any, Dict, List, Optional


_INDIA_CONTACTS = [
    {
        "label": "Emergency Response Support System (ERSS)",
        "number": "112",
        "type": "phone",
        "source_name": "Government of India ERSS",
        "source_url": "https://112.gov.in/",
    }
]


def get_emergency_contacts(country_region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return contacts configured from the supported official country registry."""
    configured_region = (
        country_region or os.getenv("EMERGENCY_COUNTRY_REGION", "IN")
    ).strip().upper()
    if configured_region in {"IN", "INDIA", "IN-IN"}:
        return [dict(contact) for contact in _INDIA_CONTACTS]
    return [
        {
            "label": "Local emergency services",
            "number": None,
            "type": "local",
            "source_name": "Configured country/region",
            "source_url": None,
            "instruction": "Use the verified emergency number for your locality.",
        }
    ]
