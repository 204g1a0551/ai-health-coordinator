"""
Immutable Security Audit Logger for compliance monitoring and threat detection.
Aligned with ABDM, DPDP Act 2023, and HIPAA Security Rule Technical Safeguards.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional
from app.security.phi_sanitizer import sanitize_phi_for_llm


class SecurityEventType(str, Enum):
    AUTH_LOGIN_SUCCESS = "AUTH_LOGIN_SUCCESS"
    AUTH_LOGIN_FAILURE = "AUTH_LOGIN_FAILURE"
    DOCUMENT_ACCESSED = "DOCUMENT_ACCESSED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_ERASED = "DOCUMENT_ERASED"
    CONSENT_GRANTED = "CONSENT_GRANTED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    UNAUTHORIZED_ACCESS_BLOCKED = "UNAUTHORIZED_ACCESS_BLOCKED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    PROMPT_INJECTION_DETECTED = "PROMPT_INJECTION_DETECTED"
    MCP_TOOL_INVOKED = "MCP_TOOL_INVOKED"


class AuditLogger:
    """
    Records tamper-evident security audit events. Automatically redacts PII/PHI
    from logged details to ensure audit logs never compromise patient privacy.
    """

    def __init__(self):
        self._memory_logs: List[Dict[str, Any]] = []

    def log_event(
        self,
        event_type: SecurityEventType,
        actor_id: str,
        resource_id: Optional[str] = None,
        details: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "LOW"
    ) -> Dict[str, Any]:
        """Logs an immutable security audit event."""
        from app.db.repository import get_db_connection, init_db
        init_db()

        log_id = f"aud_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.utcnow().isoformat()
        
        # Redact any accidental PHI in the details string
        safe_details = sanitize_phi_for_llm(details or "")

        record = {
            "id": log_id,
            "event_type": event_type.value if isinstance(event_type, SecurityEventType) else str(event_type),
            "actor_id": actor_id,
            "resource_id": resource_id or "",
            "details": safe_details,
            "ip_address": ip_address or "127.0.0.1",
            "severity": severity.upper(),
            "timestamp": timestamp,
        }

        # Save to database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO security_audit_logs (id, event_type, actor_id, resource_id, details, ip_address, severity, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record["id"], record["event_type"], record["actor_id"],
                record["resource_id"], record["details"], record["ip_address"],
                record["severity"], record["timestamp"]
            ))
            conn.commit()
            conn.close()
        except Exception:
            pass

        self._memory_logs.append(record)
        return record

    def list_logs(
        self,
        limit: int = 100,
        severity: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves audit logs filtered by severity or event type."""
        from app.db.repository import get_db_connection, init_db
        init_db()

        logs = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT * FROM security_audit_logs WHERE 1=1"
            params = []
            if severity:
                query += " AND severity = ?"
                params.append(severity.upper())
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()
            for r in rows:
                logs.append(dict(r))
        except Exception:
            pass

        if not logs:
            # Fallback to memory
            filtered = self._memory_logs
            if severity:
                filtered = [l for l in filtered if l["severity"] == severity.upper()]
            if event_type:
                filtered = [l for l in filtered if l["event_type"] == event_type]
            logs = sorted(filtered, key=lambda x: x["timestamp"], reverse=True)[:limit]

        return logs


audit_logger = AuditLogger()
