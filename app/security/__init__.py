"""
Security, Privacy & Compliance Package.
Exports core services for encryption, RBAC, PHI sanitization, prompt injection defense,
ABDM/DPDP consent management, rate limiting, and audit logging.
"""

from app.security.crypto import CryptoService, crypto_service
from app.security.rbac import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    has_permission,
    require_role,
    require_permission,
    get_current_user_context,
)
from app.security.phi_sanitizer import (
    mask_abha_id,
    mask_aadhaar,
    mask_phone,
    mask_email,
    sanitize_phi_for_llm,
    sanitize_dict_phi,
)
from app.security.prompt_guard import (
    detect_prompt_injections,
    sanitize_untrusted_medical_text,
    isolate_medical_context_for_agent,
)
from app.security.document_storage import (
    sanitize_filename,
    validate_storage_path,
    validate_file_upload,
)
from app.security.consent_manager import (
    ConsentManager,
    ConsentState,
    ConsentPurpose,
    consent_manager,
)
from app.security.retention import execute_right_to_erasure
from app.security.rate_limiter import SlidingWindowRateLimiter, rate_limiter, enforce_rate_limit
from app.security.audit import AuditLogger, SecurityEventType, audit_logger
from app.security.phi_detector import PHIDetector, phi_detector, DetectedEntity
from app.security.anonymization_vault import AnonymizationVault, anonymization_vault
from app.security.anonymizer import AnonymizationGateway, anonymization_gateway, AnonymizationResult
from app.security.audit_trail import AuditAction, AuditEvent, ImmutableAuditTrail, audit_trail

__all__ = [
    "CryptoService",
    "crypto_service",
    "UserRole",
    "Permission",
    "ROLE_PERMISSIONS",
    "has_permission",
    "require_role",
    "require_permission",
    "get_current_user_context",
    "mask_abha_id",
    "mask_aadhaar",
    "mask_phone",
    "mask_email",
    "sanitize_phi_for_llm",
    "sanitize_dict_phi",
    "detect_prompt_injections",
    "sanitize_untrusted_medical_text",
    "isolate_medical_context_for_agent",
    "sanitize_filename",
    "validate_storage_path",
    "validate_file_upload",
    "ConsentManager",
    "ConsentState",
    "ConsentPurpose",
    "consent_manager",
    "execute_right_to_erasure",
    "SlidingWindowRateLimiter",
    "rate_limiter",
    "enforce_rate_limit",
    "AuditLogger",
    "SecurityEventType",
    "audit_logger",
    "PHIDetector",
    "phi_detector",
    "DetectedEntity",
    "AnonymizationVault",
    "anonymization_vault",
    "AnonymizationGateway",
    "anonymization_gateway",
    "AnonymizationResult",
    "AuditAction",
    "AuditEvent",
    "ImmutableAuditTrail",
    "audit_trail",
]
