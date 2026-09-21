"""
Data Anonymizer & Privacy Gateway Router.
Exposes REST endpoints for controlled PII/PHI anonymization, de-anonymization,
and sensitive entity inspection.
"""

from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.security.anonymizer import anonymization_gateway, AnonymizationResult
from app.security.phi_detector import DetectedEntity
from app.security.rbac import get_current_user_context

router = APIRouter(prefix="/api/anonymizer", tags=["Data Anonymization Gateway"])


class AnonymizeRequest(BaseModel):
    text: str = Field(..., description="Sensitive text to anonymize before sending to external LLMs")
    session_id: Optional[str] = Field(None, description="Optional session ID to bind the ephemeral vault mapping")
    known_names: Optional[List[str]] = Field(None, description="Known names to prioritize for anonymization")


class DeanonymizeRequest(BaseModel):
    text: str = Field(..., description="Sanitized LLM output with surrogate tokens")
    session_id: Optional[str] = Field(None, description="Session ID containing the vault mapping")
    token_map: Optional[Dict[str, str]] = Field(None, description="Explicit surrogate-to-real token mapping")


class InspectRequest(BaseModel):
    text: str = Field(..., description="Text to scan for sensitive PII/PHI entities")
    known_names: Optional[List[str]] = Field(None, description="Known names to check against")


@router.post("/anonymize", response_model=AnonymizationResult)
def anonymize_text(
    body: AnonymizeRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Controlled Privacy Gateway:
    Scans input for sensitive PII/PHI, stores the reversible mapping in an ephemeral vault,
    and returns sanitized text containing surrogate placeholder tokens.
    """
    sid = body.session_id or user.get("id")
    result = anonymization_gateway.anonymize(
        text=body.text,
        session_id=sid,
        known_names=body.known_names
    )
    return result


@router.post("/deanonymize")
def deanonymize_text(
    body: DeanonymizeRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    De-anonymizes LLM-generated content by substituting surrogate tokens
    back to original patient values from the vault or provided mapping.
    """
    target = body.token_map or body.session_id or user.get("id")
    if not target:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'session_id' or 'token_map' must be provided for de-anonymization."
        )

    restored = anonymization_gateway.deanonymize(
        text=body.text,
        token_map_or_session_id=target
    )
    return {
        "restored_text": restored,
        "is_restored": restored != body.text
    }


@router.post("/inspect")
def inspect_text_phi(
    body: InspectRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Scans text and returns structured metadata on all detected sensitive entities.
    """
    entities = anonymization_gateway.inspect_phi(
        text=body.text,
        known_names=body.known_names
    )
    return {
        "count": len(entities),
        "entities": entities
    }


@router.get("/stats")
def get_anonymizer_stats(user: Dict[str, Any] = Depends(get_current_user_context)):
    """
    Returns telemetry and operational status of the Privacy Gateway.
    """
    return {
        "gateway_status": "ACTIVE",
        "active_vault_sessions": anonymization_gateway.vault.active_session_count(),
        "supported_categories": [
            "PATIENT_NAME",
            "DOCTOR_NAME",
            "PHONE",
            "EMAIL",
            "PATIENT_ID",
            "ABHA_ID",
            "AADHAAR",
            "INSURANCE_ID",
            "RX_ID",
            "DOB",
            "AGE",
            "ADDRESS",
            "PINCODE"
        ],
        "default_session_ttl_seconds": anonymization_gateway.vault.default_ttl
    }
