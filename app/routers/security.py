"""
Security, Privacy & Compliance Router.
Exposes endpoints for posture status, audit log inspection, ABDM consent lifecycle,
DPDP Right to Erasure, and PHI sanitization inspection.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from app.security.crypto import crypto_service
from app.security.rbac import (
    UserRole,
    Permission,
    require_role,
    require_permission,
    get_current_user_context,
)
from app.security.phi_sanitizer import sanitize_phi_for_llm, mask_abha_id, mask_phone, mask_email
from app.security.prompt_guard import detect_prompt_injections, isolate_medical_context_for_agent
from app.security.consent_manager import consent_manager, ConsentPurpose, ConsentState
from app.security.retention import execute_right_to_erasure
from app.security.rate_limiter import rate_limiter
from app.security.audit import audit_logger, SecurityEventType
from app.config import security_settings

router = APIRouter(prefix="/api/security", tags=["Security, Privacy & Compliance"])


# ── Pydantic Request/Response Models ──────────────────────────────────────────

class ConsentCreateRequest(BaseModel):
    patient_id: Optional[str] = None
    requester_id: str
    requester_name: Optional[str] = "Healthcare Provider"
    purpose: ConsentPurpose = ConsentPurpose.CARE_COORDINATION
    duration_hours: int = 72


class ErasureRequest(BaseModel):
    user_id: Optional[str] = None
    confirm: bool = Field(..., description="Must explicitly confirm irreversible data erasure")


class PHISanitizeRequest(BaseModel):
    text: str


class PromptInspectRequest(BaseModel):
    text: str
    document_name: Optional[str] = "Medical Record"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def get_security_posture(user: Dict[str, Any] = Depends(get_current_user_context)):
    """
    Returns current security, privacy, and regulatory compliance posture.
    Publicly verifiable status reflecting ABDM, DPDP, and HIPAA architectural alignment.
    """
    return {
        "status": "SECURE",
        "compliance": {
            "abdm_india_aligned": security_settings.abdm_enabled,
            "dpdp_act_2023_aligned": security_settings.dpdp_right_to_erasure_enabled,
            "hipaa_readiness": "ALIGNED_TECHNICAL_SAFEGUARDS",
            "hipaa_notice": "Software conforms to HIPAA Technical Safeguards (164.312). Organizational deployment requires signed Business Associate Agreements (BAAs).",
        },
        "encryption": {
            "in_transit": "TLS 1.3 / Strict-Transport-Security (HSTS)",
            "at_rest": "AES-256 (Fernet with PBKDF2 HMAC-SHA256)",
            "field_level_encrypted": ["phone", "abha_id", "sensitive_clinical_notes"],
        },
        "access_control": {
            "model": "Role-Based Access Control (RBAC)",
            "supported_roles": [r.value for r in UserRole],
            "caller_role": user.get("role", UserRole.PATIENT.value),
            "document_isolation": "Strict User-Level Ownership + ABDM Electronic Consent",
        },
        "controls": {
            "rate_limiting": f"Active ({security_settings.rate_limit_requests_per_minute} req/min sliding window)",
            "prompt_injection_defense": "Active (XML Delimiter Insulation + Adversarial Heuristics)",
            "audit_logging": "Active (Tamper-Evident Immutable Stream)",
            "security_headers": "Active (HSTS, CSP, X-Frame-Options DENY, nosniff)",
        }
    }


@router.get("/audit-logs")
def get_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(require_role([UserRole.ADMIN, UserRole.AUDITOR])),
):
    """
    Retrieves security audit event log stream.
    Restricted to ADMIN and AUDITOR roles only.
    """
    logs = audit_logger.list_logs(limit=limit, severity=severity, event_type=event_type)
    return {
        "count": len(logs),
        "limit": limit,
        "logs": logs,
    }


@router.post("/consents")
def create_consent_artefact(
    body: ConsentCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Creates and activates an electronic Consent Artefact under ABDM / DPDP Act 2023.
    """
    patient_id = body.patient_id or user.get("id", "usr_default_patient")
    artefact = consent_manager.grant_consent(
        patient_id=patient_id,
        requester_id=body.requester_id,
        purpose=body.purpose,
        duration_hours=body.duration_hours,
        requester_name=body.requester_name or "Healthcare Provider",
    )

    audit_logger.log_event(
        event_type=SecurityEventType.CONSENT_GRANTED,
        actor_id=patient_id,
        resource_id=artefact["id"],
        details=f"Granted {body.purpose.value} consent to requester {body.requester_id} for {body.duration_hours}h.",
        severity="MEDIUM"
    )

    return artefact


@router.get("/consents")
def list_patient_consents(
    patient_id: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Lists all electronic consent artefacts for the caller.
    """
    target_patient_id = patient_id or user.get("id", "usr_default_patient")
    consents = consent_manager.list_user_consents(target_patient_id)
    return {
        "patient_id": target_patient_id,
        "count": len(consents),
        "consents": consents
    }


@router.post("/consents/{consent_id}/revoke")
def revoke_consent_artefact(
    consent_id: str,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Instantly revokes a consent artefact.
    Implements immediate secondary access termination under DPDP Act 2023.
    """
    patient_id = user.get("id", "usr_default_patient")
    role = user.get("role", UserRole.PATIENT.value)

    success = consent_manager.revoke_consent(
        consent_id=consent_id,
        patient_id="admin" if role == UserRole.ADMIN.value else patient_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consent artefact not found or caller does not own this consent."
        )

    audit_logger.log_event(
        event_type=SecurityEventType.CONSENT_REVOKED,
        actor_id=patient_id,
        resource_id=consent_id,
        details=f"Revoked consent {consent_id}.",
        severity="HIGH"
    )

    return {
        "status": "REVOKED",
        "consent_id": consent_id,
        "revocation_effective": "IMMEDIATE"
    }


@router.post("/erasure")
def request_right_to_erasure(
    body: ErasureRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Executes DPDP Act 2023 Section 12 Right to Erasure.
    Permanently and irreversibly purges all patient records, medical documents,
    appointments, vector embeddings, and session state.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must set 'confirm': true to execute permanent data erasure."
        )

    target_user_id = body.user_id or user.get("id")
    if not target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required for data erasure."
        )

    # Verify authorization: Only the user themselves or an ADMIN can execute erasure
    caller_id = user.get("id")
    caller_role = user.get("role")
    if caller_id != target_user_id and caller_role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to erase another user's data."
        )

    result = execute_right_to_erasure(target_user_id)
    return result


@router.post("/sanitize-phi")
def preview_phi_sanitization(
    body: PHISanitizeRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Demonstrates PII/PHI sanitization and masking engine on sample text.
    """
    sanitized = sanitize_phi_for_llm(body.text)
    return {
        "original_length": len(body.text),
        "sanitized_length": len(sanitized),
        "sanitized_text": sanitized
    }


@router.post("/inspect-prompt")
def inspect_clinical_prompt(
    body: PromptInspectRequest,
    user: Dict[str, Any] = Depends(get_current_user_context)
):
    """
    Scans untrusted clinical text for adversarial prompt injection patterns
    and returns isolated XML sandbox block.
    """
    isolated_text, is_adversarial, threats = isolate_medical_context_for_agent(
        raw_document_text=body.text,
        document_name=body.document_name or "Medical Document"
    )

    if is_adversarial:
        audit_logger.log_event(
            event_type=SecurityEventType.PROMPT_INJECTION_DETECTED,
            actor_id=user.get("id", "anonymous"),
            resource_id=body.document_name,
            details=f"Prompt injection patterns detected: {', '.join(threats)}",
            severity="HIGH"
        )

    return {
        "is_adversarial": is_adversarial,
        "threats_detected": threats,
        "isolated_context": isolated_text
    }
