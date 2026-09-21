"""
Comprehensive Test Suite for Phase 36: Compliance & Immutable Audit Trail Subsystem.
Tests:
1. Exact AuditEvent schema serialization and validation
2. All 18 compliance actions coverage
3. Cryptographic Merkle hash chaining (SHA-256) from genesis block
4. Verification of chain integrity (valid vs tampered database records)
5. Zero-PHI redaction enforcement in audit logging
6. REST API Endpoints:
   - GET /api/audit/events (RBAC protection: AUDITOR / ADMIN vs PATIENT 403)
   - GET /api/audit/verify-integrity
   - GET /api/audit/stats
   - GET /api/audit/export
"""

import os
import sys
import unittest
import datetime
import jwt
from fastapi.testclient import TestClient

# Ensure root & backend directories are in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from app.config import auth_settings
from app.security.audit_trail import (
    AuditAction,
    AuditEvent,
    ImmutableAuditTrail,
    audit_trail,
    compute_audit_hash,
)
from app.db.repository import get_db_connection


class TestComplianceAuditTrail(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

        # Generate tokens for RBAC testing
        now = datetime.datetime.utcnow()
        exp = now + datetime.timedelta(hours=2)

        cls.admin_token = jwt.encode(
            {"sub": "user-admin-01", "email": "admin@hospital.org", "role": "ADMIN", "exp": exp},
            auth_settings.jwt_secret,
            algorithm=auth_settings.jwt_algorithm,
        )
        cls.auditor_token = jwt.encode(
            {"sub": "user-auditor-01", "email": "auditor@compliance.gov.in", "role": "AUDITOR", "exp": exp},
            auth_settings.jwt_secret,
            algorithm=auth_settings.jwt_algorithm,
        )
        cls.patient_token = jwt.encode(
            {"sub": "user-patient-01", "email": "patient@example.com", "role": "PATIENT", "exp": exp},
            auth_settings.jwt_secret,
            algorithm=auth_settings.jwt_algorithm,
        )

        # Ensure clean state for cryptographic chain tests
        try:
            conn = get_db_connection()
            conn.cursor().execute("DELETE FROM audit_trail_events")
            conn.commit()
            conn.close()
        except Exception:
            pass

    def test_all_18_compliance_actions_defined(self):
        """Verify that all 18 actions requested for Phase 36 compliance are defined."""
        required_actions = {
            "LOGIN",
            "LOGOUT",
            "DOCUMENT_UPLOADED",
            "DOCUMENT_ACCESSED",
            "DOCUMENT_DOWNLOADED",
            "DOCUMENT_DELETED",
            "MEDICAL_RECORD_ACCESSED",
            "LLM_REQUEST",
            "LLM_RESPONSE",
            "MCP_TOOL_CALLED",
            "MCP_TOOL_FAILED",
            "APPOINTMENT_CREATED",
            "APPOINTMENT_CANCELLED",
            "PRESCRIPTION_ANALYZED",
            "BILL_ANALYZED",
            "INSURANCE_POLICY_ACCESSED",
            "DDI_CHECK_PERFORMED",
            "MEDICINE_INFORMATION_REQUESTED",
        }
        enum_values = {a.value for a in AuditAction}
        for action in required_actions:
            self.assertIn(action, enum_values, f"Required action {action} missing from AuditAction enum")

    def test_audit_event_exact_schema(self):
        """Verify AuditEvent produces the exact user-specified JSON schema."""
        event = AuditEvent(
            event_id="AUD-82931",
            user_id="USER-104",
            action=AuditAction.DOCUMENT_ACCESSED,
            resource_type="MEDICAL_DOCUMENT",
            resource_id="DOC-8392",
            timestamp="2026-09-21T18:30:00Z",
            purpose="INSURANCE_ANALYSIS",
            result="SUCCESS",
            details="document_id=DOC-8392 agent=DOCUMENT_AGENT",
        )
        data = event.dict()
        self.assertEqual(data["event_id"], "AUD-82931")
        self.assertEqual(data["user_id"], "USER-104")
        self.assertEqual(data["action"], "DOCUMENT_ACCESSED")
        self.assertEqual(data["resource_type"], "MEDICAL_DOCUMENT")
        self.assertEqual(data["resource_id"], "DOC-8392")
        self.assertEqual(data["timestamp"], "2026-09-21T18:30:00Z")
        self.assertEqual(data["purpose"], "INSURANCE_ANALYSIS")
        self.assertEqual(data["result"], "SUCCESS")

    def test_record_event_and_merkle_chain(self):
        """Test recording events and verifying SHA-256 Merkle chain linking."""
        test_audit = ImmutableAuditTrail()

        evt1 = test_audit.record_event(
            action=AuditAction.LOGIN,
            user_id="TEST-USER-1",
            resource_type="AUTH_SESSION",
            resource_id="sess-001",
            purpose="AUTHENTICATION",
            result="SUCCESS",
        )
        self.assertTrue(evt1.event_id.startswith("AUD-"))
        self.assertIsNotNone(evt1.record_hash)
        self.assertEqual(len(evt1.record_hash), 64)

        evt2 = test_audit.record_event(
            action=AuditAction.DOCUMENT_UPLOADED,
            user_id="TEST-USER-1",
            resource_type="MEDICAL_DOCUMENT",
            resource_id="doc-001",
            purpose="CARE_COORDINATION",
            result="SUCCESS",
        )
        self.assertEqual(evt2.previous_hash, evt1.record_hash)

        evt3 = test_audit.record_event(
            action=AuditAction.PRESCRIPTION_ANALYZED,
            user_id="TEST-USER-1",
            resource_type="CLINICAL_ARTIFACT",
            resource_id="doc-001",
            purpose="PRESCRIPTION_ANALYSIS",
            result="SUCCESS",
        )
        self.assertEqual(evt3.previous_hash, evt2.record_hash)

    def test_zero_phi_enforcement(self):
        """Test that raw clinical diagnostic and medical details are redacted from audit logs."""
        test_audit = ImmutableAuditTrail()

        raw_details = "Patient has diabetes and takes Metformin. symptoms: high fever and severe cough"
        evt = test_audit.record_event(
            action=AuditAction.DOCUMENT_ACCESSED,
            user_id="TEST-USER-2",
            resource_type="MEDICAL_DOCUMENT",
            resource_id="DOC-999",
            purpose="TREATMENT",
            details=raw_details,
        )

        # Must NOT contain raw clinical strings
        self.assertNotIn("diabetes", evt.details.lower())
        self.assertNotIn("high fever", evt.details.lower())
        self.assertIn("[CLINICAL_DATA_REDACTED]", evt.details)

    def test_verify_chain_integrity_untampered(self):
        """Test verify_chain_integrity returns valid for untampered chain."""
        verification = audit_trail.verify_chain_integrity()
        self.assertTrue(verification["valid"])
        self.assertFalse(verification["tampered"])
        self.assertGreaterEqual(verification["total_records_verified"], 0)

    def test_verify_chain_integrity_detects_tampering(self):
        """Test that altering any record in SQLite invalidates the Merkle hash chain."""
        # Insert a deliberate canary event
        canary = audit_trail.record_event(
            action=AuditAction.MCP_TOOL_CALLED,
            user_id="CANARY-USER",
            resource_type="MCP_TOOL",
            resource_id="canary_tool",
            purpose="TAMPER_TEST",
            result="SUCCESS",
        )

        # Tamper directly in SQLite database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE audit_trail_events SET action = 'LOGOUT' WHERE event_id = ?",
                (canary.event_id,),
            )
            conn.commit()

            # Verification should now fail and flag tampering
            tamper_report = audit_trail.verify_chain_integrity()
            self.assertFalse(tamper_report["valid"])
            self.assertTrue(tamper_report["tampered"])
            self.assertEqual(tamper_report["tampered_event_id"], canary.event_id)

            # Restore the tampered record to maintain test cleanliness
            cursor.execute(
                "UPDATE audit_trail_events SET action = 'MCP_TOOL_CALLED' WHERE event_id = ?",
                (canary.event_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def test_api_rbac_events_endpoint(self):
        """Verify that only AUDITOR or ADMIN can access audit trail events."""
        # Patient token -> 403 Forbidden
        res_patient = self.client.get(
            "/api/audit/events",
            headers={"Authorization": f"Bearer {self.patient_token}"},
        )
        self.assertEqual(res_patient.status_code, 403)

        # Auditor token -> 200 OK
        res_auditor = self.client.get(
            "/api/audit/events",
            headers={"Authorization": f"Bearer {self.auditor_token}"},
        )
        self.assertEqual(res_auditor.status_code, 200)
        data = res_auditor.json()
        self.assertIn("count", data)
        self.assertIn("events", data)

        # Admin token -> 200 OK
        res_admin = self.client.get(
            "/api/audit/events",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(res_admin.status_code, 200)

    def test_api_verify_integrity_endpoint(self):
        """Test GET /api/audit/verify-integrity endpoint."""
        res = self.client.get(
            "/api/audit/verify-integrity",
            headers={"Authorization": f"Bearer {self.auditor_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("valid", data)
        self.assertTrue(data["valid"])
        self.assertFalse(data["tampered"])

    def test_api_stats_endpoint(self):
        """Test GET /api/audit/stats endpoint."""
        res = self.client.get(
            "/api/audit/stats",
            headers={"Authorization": f"Bearer {self.auditor_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_recorded_events", data)
        self.assertIn("events_by_action", data)
        self.assertIn("hash_chain_status", data)

    def test_api_export_endpoint(self):
        """Test GET /api/audit/export endpoint for compliance reporting."""
        res = self.client.get(
            "/api/audit/export",
            headers={"Authorization": f"Bearer {self.auditor_token}"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["report_type"], "HEALTHCARE_IMMUTABLE_AUDIT_REPORT")
        self.assertIn("standards_aligned", data)
        self.assertIn("integrity_attestation", data)
        self.assertIn("audit_events", data)


if __name__ == "__main__":
    unittest.main()
