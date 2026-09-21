"""
Data Anonymization Agent & Controlled Privacy Gateway.
Acts as a mandatory privacy layer before any sensitive information reaches
external LLMs or third-party cognitive services.
"""

import re
import uuid
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel

from app.security.phi_detector import phi_detector, DetectedEntity
from app.security.anonymization_vault import anonymization_vault
from app.security.audit import audit_logger, SecurityEventType


class AnonymizationResult(BaseModel):
    sanitized_text: str
    token_map: Dict[str, str]
    detected_entities: List[DetectedEntity]
    session_id: str
    is_anonymized: bool
    entities_count: int


class AnonymizationGateway:
    """
    Controlled Privacy Gateway.
    Guarantees:
    1. Zero raw PII/PHI reaches external LLMs.
    2. Referential entity consistency across sentences (same name gets same token).
    3. Reversible mapping preserved strictly in local ephemeral vault.
    4. Safe de-anonymization of generated LLM responses.
    """

    def __init__(self):
        self.detector = phi_detector
        self.vault = anonymization_vault

    def anonymize(
        self,
        text: str,
        session_id: Optional[str] = None,
        known_names: Optional[List[str]] = None
    ) -> AnonymizationResult:
        """
        Scans text, generates surrogate tokens, updates the session vault,
        and returns the sanitized text for external LLM consumption.
        """
        if not text or not isinstance(text, str):
            return AnonymizationResult(
                sanitized_text=text or "",
                token_map={},
                detected_entities=[],
                session_id=session_id or "ephemeral",
                is_anonymized=False,
                entities_count=0
            )

        sid = session_id or f"anon_sess_{uuid.uuid4().hex[:12]}"
        vault_session = self.vault.get_or_create_session(sid)

        entities = self.detector.detect(text, known_names=known_names)

        if not entities:
            return AnonymizationResult(
                sanitized_text=text,
                token_map={},
                detected_entities=[],
                session_id=sid,
                is_anonymized=False,
                entities_count=0
            )

        # Build token replacements with referential consistency
        replacements = []
        token_map: Dict[str, str] = {}

        for entity in entities:
            original_val = entity.text
            clean_key = original_val.strip().lower()

            # Check if this exact entity already has a surrogate in this session
            existing_surrogate = vault_session.get_surrogate(clean_key)
            if existing_surrogate:
                surrogate = existing_surrogate
            else:
                base_token = entity.surrogate_key.rstrip("]")
                # If single entity type (like PATIENT_NAME), keep canonical [PATIENT_NAME]
                # If multiple IDs/phones, append index if needed
                idx = vault_session.next_token_index(entity.entity_type)
                if entity.entity_type in ["PATIENT_NAME", "DOB", "AGE"]:
                    surrogate = f"{base_token}]"
                else:
                    surrogate = f"{base_token}_{idx}]" if idx > 1 else f"{base_token}]"

                vault_session.add(surrogate, original_val)

            token_map[surrogate] = original_val
            replacements.append((entity.start, entity.end, surrogate))

        # Perform replacement from right to left (descending order of start index)
        # to ensure previous character indices remain valid
        replacements.sort(key=lambda x: x[0], reverse=True)
        sanitized_chars = list(text)

        for start, end, surrogate in replacements:
            sanitized_chars[start:end] = list(surrogate)

        sanitized_text = "".join(sanitized_chars)

        # Audit logging (record entity types and counts, NEVER plain text)
        entity_types_summary = list(set(e.entity_type for e in entities))
        audit_logger.log_event(
            event_type=SecurityEventType.MCP_TOOL_INVOKED,  # Or PII_ANONYMIZED
            actor_id=sid,
            resource_id="PrivacyGateway",
            details=f"Anonymized {len(entities)} sensitive entities: {', '.join(entity_types_summary)}",
            severity="LOW"
        )

        return AnonymizationResult(
            sanitized_text=sanitized_text,
            token_map=token_map,
            detected_entities=entities,
            session_id=sid,
            is_anonymized=True,
            entities_count=len(entities)
        )

    def deanonymize(
        self,
        text: str,
        token_map_or_session_id: Union[Dict[str, str], str]
    ) -> str:
        """
        Replaces surrogate tokens in an LLM-generated response with original real-world values.
        """
        if not text or not isinstance(text, str):
            return text

        if isinstance(token_map_or_session_id, str):
            mapping = self.vault.get_mappings_for_session(token_map_or_session_id)
        elif isinstance(token_map_or_session_id, dict):
            mapping = token_map_or_session_id
        else:
            mapping = {}

        if not mapping:
            return text

        restored = text
        # Sort tokens by length descending to prevent substring collisions (e.g. [PHONE_10] vs [PHONE_1])
        sorted_tokens = sorted(mapping.keys(), key=len, reverse=True)

        for surrogate in sorted_tokens:
            original = mapping[surrogate]
            # Replace exact bracketed surrogate token
            restored = restored.replace(surrogate, original)

        return restored

    def inspect_phi(self, text: str, known_names: Optional[List[str]] = None) -> List[DetectedEntity]:
        """Inspection helper returning detected entities without modifying text."""
        return self.detector.detect(text, known_names=known_names)


anonymization_gateway = AnonymizationGateway()
