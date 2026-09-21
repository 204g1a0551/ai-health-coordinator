"""
Comprehensive Automated Test Suite for Phase 35: Data Anonymization Agent & Privacy Gateway.
Tests deterministic PII/PHI detection, surrogate tokenization, referential consistency,
session vault isolation, two-way de-anonymization, and REST API endpoints.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from app.security.phi_detector import PHIDetector, phi_detector
from app.security.anonymization_vault import AnonymizationVault, anonymization_vault
from app.security.anonymizer import AnonymizationGateway, anonymization_gateway


class TestDataAnonymizationGateway(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.detector = phi_detector
        cls.gateway = anonymization_gateway

    def setUp(self):
        # Clear vault before each test
        self.gateway.vault.purge_all()

    # ── 1. Deterministic Entity Detection Tests ───────────────────────────────

    def test_user_example_detection(self):
        """Validates the exact example provided in the user's specification."""
        doc = (
            "Patient: Mahesh Kumar\n"
            "Phone: 9876543210\n"
            "Email: mahesh@example.com\n"
            "Patient ID: P123456\n\n"
            "Symptoms:\n"
            "Fever for 2 days"
        )
        entities = self.detector.detect(doc)
        types = {e.entity_type: e.text for e in entities}

        self.assertIn("PATIENT_NAME", types)
        self.assertEqual(types["PATIENT_NAME"], "Mahesh Kumar")
        self.assertIn("PHONE", types)
        self.assertEqual(types["PHONE"], "9876543210")
        self.assertIn("EMAIL", types)
        self.assertEqual(types["EMAIL"], "mahesh@example.com")
        self.assertIn("PATIENT_ID", types)
        self.assertEqual(types["PATIENT_ID"], "P123456")

    def test_clinical_terms_safeguard(self):
        """Clinical symptoms, disease names, and medications must NEVER be masked."""
        clinical_text = "Patient reports fever, cough, diabetes, and hypertension. Prescribed Paracetamol and Metformin in Cardiology."
        entities = self.detector.detect(clinical_text)
        detected_texts = [e.text.lower() for e in entities]

        for safe_word in ["fever", "cough", "diabetes", "hypertension", "paracetamol", "metformin", "cardiology"]:
            self.assertNotIn(safe_word, detected_texts)

    def test_national_and_insurance_ids_detection(self):
        text = (
            "ABHA ID: 91-1234-5678-9012, Aadhaar: 1234 5678 9012. "
            "Policy No: POL-998877, Prescription ID: RX-102938. "
            "DOB: 15-Aug-1990, Age: 34."
        )
        entities = self.detector.detect(text)
        types = {e.entity_type for e in entities}

        self.assertIn("ABHA_ID", types)
        self.assertIn("AADHAAR", types)
        self.assertIn("INSURANCE_ID", types)
        self.assertIn("RX_ID", types)
        self.assertIn("DOB", types)
        self.assertIn("AGE", types)

    # ── 2. Surrogate Tokenization & Anonymization Tests ───────────────────────

    def test_user_example_anonymization(self):
        """Tests that text is accurately converted to surrogate placeholders."""
        doc = (
            "Patient: Mahesh Kumar\n"
            "Phone: 9876543210\n"
            "Email: mahesh@example.com\n"
            "Patient ID: P123456\n\n"
            "Symptoms:\n"
            "Fever for 2 days"
        )
        result = self.gateway.anonymize(doc, session_id="test_sess_01")
        sanitized = result.sanitized_text

        # Identifiable information must be completely gone
        self.assertNotIn("Mahesh Kumar", sanitized)
        self.assertNotIn("9876543210", sanitized)
        self.assertNotIn("mahesh@example.com", sanitized)
        self.assertNotIn("P123456", sanitized)

        # Surrogates must be present
        self.assertIn("[PATIENT_NAME]", sanitized)
        self.assertIn("[PHONE]", sanitized)
        self.assertIn("[EMAIL]", sanitized)
        self.assertIn("[PATIENT_ID]", sanitized)

        # Non-sensitive symptoms must remain unaltered
        self.assertIn("Fever for 2 days", sanitized)

    def test_referential_consistency(self):
        """Repeating the same entity across sentences must assign the same surrogate token."""
        text = "Mahesh Kumar came for a checkup. Mahesh Kumar was advised rest. Contact Mahesh Kumar tomorrow."
        result = self.gateway.anonymize(text, session_id="test_sess_ref", known_names=["Mahesh Kumar"])
        sanitized = result.sanitized_text

        self.assertNotIn("Mahesh Kumar", sanitized)
        count_tokens = sanitized.count("[PATIENT_NAME]")
        self.assertEqual(count_tokens, 3)

    # ── 3. De-anonymization & Two-Way Restoration ────────────────────────────

    def test_deanonymization_of_llm_response(self):
        """Simulates external LLM referring to surrogate tokens and verifies clean restoration."""
        # 1. Anonymize original
        original = "Patient: Mahesh Kumar, Phone: 9876543210. Symptoms: Fever for 2 days."
        anon_result = self.gateway.anonymize(original, session_id="test_sess_llm")

        # 2. Simulated response from external LLM referencing surrogates
        llm_response = "Patient [PATIENT_NAME] reports fever for 2 days. A confirmation SMS was sent to [PHONE]."

        # 3. De-anonymize response using the session vault
        restored = self.gateway.deanonymize(llm_response, session_id="test_sess_llm")

        self.assertEqual(
            restored,
            "Patient Mahesh Kumar reports fever for 2 days. A confirmation SMS was sent to 9876543210."
        )

    def test_full_roundtrip_fidelity(self):
        """Full roundtrip anonymize -> deanonymize should reproduce original text."""
        doc = "Doctor: Dr. Ravi Kumar examined patient with ABHA ID: 91-1234-5678-9012 and Email: test@patient.org."
        anon = self.gateway.anonymize(doc, session_id="roundtrip_sess")
        restored = self.gateway.deanonymize(anon.sanitized_text, session_id="roundtrip_sess")

        self.assertEqual(restored, doc)

    # ── 4. Session Vault Isolation & Expiry Tests ─────────────────────────────

    def test_vault_session_isolation(self):
        """Session A and Session B must have isolated mappings."""
        text_a = "Patient: Alice Smith, Phone: 9111111111."
        text_b = "Patient: Bob Jones, Phone: 9222222222."

        self.gateway.anonymize(text_a, session_id="sess_A")
        self.gateway.anonymize(text_b, session_id="sess_B")

        llm_msg = "Hello [PATIENT_NAME], we have your phone as [PHONE]."

        restored_a = self.gateway.deanonymize(llm_msg, session_id="sess_A")
        restored_b = self.gateway.deanonymize(llm_msg, session_id="sess_B")

        self.assertIn("Alice Smith", restored_a)
        self.assertNotIn("Bob Jones", restored_a)

        self.assertIn("Bob Jones", restored_b)
        self.assertNotIn("Alice Smith", restored_b)

    def test_vault_purge(self):
        """Purging a session makes de-anonymization return tokens unchanged."""
        text = "Patient: Mahesh Kumar."
        anon = self.gateway.anonymize(text, session_id="sess_purge")
        self.gateway.vault.purge_session("sess_purge")

        # After purge, vault cannot de-anonymize
        restored = self.gateway.deanonymize(anon.sanitized_text, session_id="sess_purge")
        self.assertEqual(restored, anon.sanitized_text)

    # ── 5. REST API Endpoints Tests ──────────────────────────────────────────

    def test_api_anonymize_endpoint(self):
        payload = {
            "text": "Patient: Mahesh Kumar\nPhone: 9876543210\nPatient ID: P123456",
            "session_id": "api_test_sess"
        }
        resp = self.client.post("/api/anonymizer/anonymize", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_anonymized"])
        self.assertIn("[PATIENT_NAME]", data["sanitized_text"])
        self.assertIn("[PHONE]", data["sanitized_text"])
        self.assertIn("[PATIENT_ID]", data["sanitized_text"])
        self.assertNotIn("Mahesh Kumar", data["sanitized_text"])

    def test_api_deanonymize_endpoint(self):
        # 1. Anonymize first
        payload = {
            "text": "Patient: Sarah Connor, Phone: 9876543210",
            "session_id": "api_deanom_sess"
        }
        self.client.post("/api/anonymizer/anonymize", json=payload)

        # 2. Call deanonymize
        deanon_payload = {
            "text": "Appointment booked for [PATIENT_NAME] at [PHONE].",
            "session_id": "api_deanom_sess"
        }
        resp = self.client.post("/api/anonymizer/deanonymize", json=deanon_payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_restored"])
        self.assertEqual(data["restored_text"], "Appointment booked for Sarah Connor at 9876543210.")

    def test_api_inspect_endpoint(self):
        resp = self.client.post("/api/anonymizer/inspect", json={
            "text": "Patient: Mahesh Kumar, Email: mahesh@test.com, PID: P9988"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 3)
        types = [e["entity_type"] for e in data["entities"]]
        self.assertIn("PATIENT_NAME", types)
        self.assertIn("EMAIL", types)
        self.assertIn("PATIENT_ID", types)

    def test_api_stats_endpoint(self):
        resp = self.client.get("/api/anonymizer/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["gateway_status"], "ACTIVE")
        self.assertIn("PATIENT_NAME", data["supported_categories"])
        self.assertIn("INSURANCE_ID", data["supported_categories"])


if __name__ == "__main__":
    unittest.main()
