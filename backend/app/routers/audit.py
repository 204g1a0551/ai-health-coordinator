"""
Compliance & Immutable Audit Trail Router.
Exposes REST endpoints for audit event inspection, cryptographic hash-chain integrity verification,
metrics aggregation, and compliance reporting (ABDM, DPDP Act 2023, HIPAA Security Rule).
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from app.security.audit_trail import audit_trail, AuditAction, AuditEvent
from app.security.rbac import UserRole, require_role, get_current_user_context

router = APIRouter(prefix="/api/audit", tags=["Compliance & Immutable Audit Trail"])


@router.get("/events")
def get_audit_trail_events(
    action: Optional[str] = Query(None, description="Filter by AuditAction (e.g. DOCUMENT_ACCESSED, LOGIN)"),
    user_id: Optional[str] = Query(None, description="Filter by actor / user ID"),
    resource_type: Optional[str] = Query(None, description="Filter by resource category"),
    result: Optional[str] = Query(None, description="Filter by outcome (SUCCESS, FAILURE, BLOCKED)"),
    limit: int = Query(100, ge=1, le=500, description="Max events to return"),
    user: Dict[str, Any] = Depends(require_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Retrieves filtered immutable audit events.
    Access strictly restricted to ADMIN and AUDITOR roles.
    Zero PHI guarantee: Returns non-sensitive audit metadata only.
    """
    events = audit_trail.query_events(
        action=action,
        user_id=user_id,
        resource_type=resource_type,
        result=result,
        limit=limit
    )
    return {
        "count": len(events),
        "limit": limit,
        "events": events
    }


@router.get("/verify-integrity")
def verify_audit_hash_chain(
    user: Dict[str, Any] = Depends(require_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Cryptographic verification endpoint.
    Recalculates SHA-256 Merkle chain across all stored events from genesis.
    Returns mathematical proof that zero records have been altered, deleted, or inserted.
    """
    report = audit_trail.verify_chain_integrity()
    return report


@router.get("/stats")
def get_audit_trail_stats(
    user: Dict[str, Any] = Depends(require_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Returns operational audit metrics, activity breakdown, and hash chain status.
    """
    return audit_trail.get_stats()


@router.get("/export")
def export_compliance_report(
    user: Dict[str, Any] = Depends(require_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Exports a structured audit compliance report certified with cryptographic integrity proof.
    Ready for ABDM, DPDP, or HIPAA regulatory reviews.
    """
    return audit_trail.export_compliance_report()
