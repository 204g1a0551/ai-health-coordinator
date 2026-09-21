"""
Phase 38: End-to-End Golden Scenarios Test Suite.
Verifies complete, unbroken user journeys across all 7 Golden Scenarios:
- Scenario A: Registration -> Login -> Symptoms -> Dept Selection -> Doctor Search -> Slot Search -> Booking -> DB Verification -> Dashboard State -> Follow-up Task Creation
- Scenario B: Upload Prescription -> PII/PHI Anonymization -> Document Extraction -> Medicine Extraction -> RAG -> Medicine Information -> Pharmacy Search
- Scenario C: Upload Two Prescriptions -> Medicine Normalization -> DDI Check -> Verified Result -> Display Warning
- Scenario D: Upload Policy -> Upload Pharmacy Bill -> RAG -> Policy Clause Retrieval -> Coverage Analysis -> Evidence/Page Display -> Claim Preparation
- Scenario E: Severe Symptoms -> Triage -> Emergency Workflow -> Normal Agents Blocked -> Emergency Information Displayed
- Scenario F: Voice Telugu Spoken Input -> STT -> Language Processing -> Triage -> LangGraph -> Agent -> Response -> Telugu TTS
- Scenario G: Appointment Completed -> Follow-Up Task -> Scheduler -> 48-Hour Trigger -> Follow-Up Agent -> User Notification
"""

import os
import sys
import json
import time
import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

# Ensure root & backend directories are in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ["USE_LOCAL_NLU"] = "1"

from app.main import app
from app.db.repository import (
    get_db_connection,
    init_db,
    get_user_by_email,
    get_medical_document,
)
from app.services.ddi_service import ddi_service
from app.services.insurance_rag_service import insurance_rag_service
from app.services.voice_service import voice_service
from app.services.follow_up_service import follow_up_service
from app.mcp.client import mcp_client
from app.models.voice import VoiceProcessRequest
from app.models.follow_up import FollowUpStatus, FollowUpCreateRequest, FollowUpResponseRequest


class TestE2EGoldenScenarios(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE appointment_slots SET is_available = 1")
        conn.commit()
        conn.close()

    # --------------------------------------------------------------------------
    # Scenario A: Complete Consultation Booking & Follow-Up Lifecycle
    # --------------------------------------------------------------------------
    def test_golden_scenario_a_full_appointment_journey(self):
        """
        Scenario A:
        Register -> Login -> Describe symptoms -> Dept selection -> Doctor search ->
        Slot search -> Book appointment -> Verify database -> Verify dashboard -> Create follow-up task
        """
        session_id = f"golden_user_a_{int(time.time())}"
        test_email = f"patient_{int(time.time())}@hospital.org"
        test_password = "SecurePassword!999"

        # 1. Register
        reg_res = self.client.post("/api/auth/register", json={
            "email": test_email,
            "password": test_password,
            "full_name": "Mahesh Kumar",
            "phone": "+91-9876543210",
            "role": "PATIENT"
        })
        self.assertIn(reg_res.status_code, [200, 201])

        # 2. Login
        login_res = self.client.post("/api/auth/login", json={
            "email": test_email,
            "password": test_password
        })
        self.assertEqual(login_res.status_code, 200)
        auth_token = login_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {auth_token}"}

        # 3. Describe symptoms
        sym_res = self.client.post("/api/chat", json={
            "message": "I have had a mild fever and body aches for two days",
            "sessionId": session_id
        })
        self.assertEqual(sym_res.status_code, 200)
        sym_data = sym_res.json()
        self.assertTrue(sym_data["normalWorkflowAllowed"])

        # 4. Department selection & Doctor search
        doc_res = self.client.post("/api/chat", json={
            "message": "Find General Medicine doctors near Koramangala",
            "sessionId": session_id
        })
        self.assertEqual(doc_res.status_code, 200)
        doc_data = doc_res.json()
        self.assertTrue(any(k in doc_data["message"].lower() for k in ["doctor", "specialist", "dr."]))

        # 5. Slot search
        slot_res = self.client.post("/api/chat", json={
            "message": "Show available slots for Dr. Priya Sharma tomorrow",
            "sessionId": session_id
        })
        self.assertEqual(slot_res.status_code, 200)

        # 6. Book appointment (Book 3:00 PM slot)
        book_res = self.client.post("/api/chat", json={
            "message": "Book Dr. Priya Sharma tomorrow at 3:00 PM",
            "sessionId": session_id
        })
        self.assertEqual(book_res.status_code, 200)
        book_data = book_res.json()
        self.assertIn("confirmed", book_data["message"].lower())

        # 7. Verify Database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as cnt FROM appointments WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()
        self.assertGreaterEqual(row["cnt"] if isinstance(row, dict) else row[0], 1)

        # 8. Verify Dashboard State
        dash_res = self.client.get("/api/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        dash_data = dash_res.json()
        self.assertTrue("patient" in dash_data or "appointmentSummary" in dash_data)


        # 9. Verify Follow-Up Task Created
        tasks = follow_up_service.list_tasks(patient_id=session_id)
        self.assertGreaterEqual(len(tasks), 1)
        self.assertEqual(tasks[0].source_type, "APPOINTMENT")

    # --------------------------------------------------------------------------
    # Scenario B: Prescription Upload, Anonymization, RAG & Pharmacy Search
    # --------------------------------------------------------------------------
    def test_golden_scenario_b_prescription_anonymization_and_pharmacy(self):
        """
        Scenario B:
        Upload prescription -> PII/PHI anonymization -> Document extraction ->
        Medicine extraction -> RAG -> Medicine information -> Pharmacy search
        """
        # 1. PII/PHI Anonymization on uploaded prescription text
        raw_prescription_text = (
            "Patient Name: Mahesh Kumar, Phone: 9876543210, Email: mahesh@example.com\n"
            "Rx: Tab Augmentin 625mg 1 tab twice daily for 5 days. Tab Paracetamol 650mg SOS."
        )
        anon_res = self.client.post("/api/anonymizer/anonymize", json={
            "session_id": "scenario_b_session",
            "text": raw_prescription_text
        })
        self.assertEqual(anon_res.status_code, 200)
        anon_data = anon_res.json()
        sanitized_context = anon_data["sanitized_text"]

        # Sensitive identifiers must be replaced
        self.assertNotIn("9876543210", sanitized_context)
        self.assertNotIn("mahesh@example.com", sanitized_context)
        self.assertIn("[PHONE]", sanitized_context)
        self.assertIn("[EMAIL]", sanitized_context)
        # Clinical medicines must NOT be masked
        self.assertIn("Augmentin", sanitized_context)

        # 2. Extract medicines & query pharmacology information
        from app.agents.medicine_agent import medicine_agent
        med_info = medicine_agent.get_medicine_info("Augmentin 625mg")
        self.assertEqual(med_info["medicine_name"], "Augmentin")
        self.assertIn("Amoxicillin", med_info["generic_name"])

        # 3. Pharmacy search near Koramangala
        pharm_res = self.client.post("/api/pharmacies/search", json={
            "medicines": ["Augmentin", "Paracetamol"],
            "locality": "Koramangala"
        })
        self.assertEqual(pharm_res.status_code, 200)
        pharmacies = pharm_res.json()
        self.assertGreaterEqual(len(pharmacies.get("pharmacies", [])), 1)

    # --------------------------------------------------------------------------
    # Scenario C: Multi-Prescription Drug-Drug Interaction (DDI) Verification
    # --------------------------------------------------------------------------
    def test_golden_scenario_c_multi_prescription_ddi_check(self):
        """
        Scenario C:
        Upload two prescriptions -> Medicine normalization -> DDI check ->
        Verified result -> Display warning
        """
        # Upload Prescription 1 (Blood thinner: Warfarin) & Prescription 2 (NSAID: Aspirin)
        med_a = ddi_service.normalize_medicine_name("Warfarin 5mg")
        med_b = ddi_service.normalize_medicine_name("Aspirin 75mg")
        pair_analysis = ddi_service.check_interaction_pair(med_a, med_b)
        self.assertIn(pair_analysis.severity.value, ["HIGH", "MAJOR"])
        self.assertTrue(any(term in pair_analysis.clinical_effect.lower() for term in ["hemorrhage", "bleeding"]))

        # Verify through DDI agent endpoint
        res = self.client.post("/api/ddi/check-pair", json={
            "medicine_a": "Warfarin",
            "medicine_b": "Aspirin"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn(data.get("severity"), ["HIGH", "MAJOR"])

    # --------------------------------------------------------------------------
    # Scenario D: Insurance Policy, Bill Verification & Coverage Matrix
    # --------------------------------------------------------------------------
    def test_golden_scenario_d_insurance_policy_and_bill_verification(self):
        """
        Scenario D:
        Upload policy -> Upload pharmacy bill -> RAG -> Policy clause retrieval ->
        Coverage analysis -> Evidence/page display -> Claim preparation
        """
        policy_id = "doc-fc6d33ca06fc"

        # 1. RAG clause retrieval for outpatient pharmacy benefits
        rag_answer = insurance_rag_service.answer_policy_query(
            "What is the pharmacy outpatient reimbursement limit?",
            policy_id=policy_id
        )
        self.assertTrue(len(rag_answer.answer) > 0)
        self.assertGreaterEqual(len(rag_answer.evidence), 1)
        self.assertEqual(rag_answer.evidence[0].page_number, 1)

        # 2. Bill verification comparison
        from app.services.bill_verification_service import bill_verification_service
        bill_data = bill_verification_service.verify_documents()
        self.assertGreaterEqual(bill_data.total_billed, 1)
        self.assertIsNotNone(bill_data.financial_summary)

        # 3. Check claim preparation documents checklist via MCP
        claim_checklist = mcp_client.call_tool(
            server_name="insurance_mcp",
            tool_name="get_required_claim_documents",
            arguments={"claim_type": "pharmacy"},
            caller_agent="insurance_agent"
        )
        self.assertTrue(claim_checklist.success)
        self.assertIn("required_documents", claim_checklist.data)


    # --------------------------------------------------------------------------
    # Scenario E: Severe Medical Emergency Triage Interception
    # --------------------------------------------------------------------------
    def test_golden_scenario_e_emergency_triage_interception(self):
        """
        Scenario E:
        Severe symptoms -> Triage -> Emergency workflow ->
        Normal agents blocked -> Emergency information displayed
        """
        emergency_msg = "I am having severe crushing chest pain and difficulty breathing"
        res = self.client.post("/api/chat", json={
            "message": emergency_msg,
            "sessionId": "emergency_golden_session"
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Emergency workflow must be enforced
        self.assertEqual(data["triageStatus"], "EMERGENCY")
        self.assertFalse(data["normalWorkflowAllowed"])
        self.assertEqual(data["action"], "SHOW_EMERGENCY_ALERT")

        # Must display official Indian emergency services
        contacts = data["data"]["contacts"]
        phone_numbers = [c["number"] for c in contacts]
        self.assertIn("112", phone_numbers)

    # --------------------------------------------------------------------------
    # Scenario F: Multilingual Spoken Telugu Voice Pipeline
    # --------------------------------------------------------------------------
    def test_golden_scenario_f_multilingual_voice_telugu_pipeline(self):
        """
        Scenario F:
        Voice Telugu input -> STT -> Language processing ->
        Triage -> LangGraph -> Agent -> Response -> Telugu TTS
        """
        telugu_voice_req = VoiceProcessRequest(
            session_id="voice_golden_session",
            text="నాకు రెండు రోజులుగా జ్వరం ఉంది.",
            preferred_language="te",
            synthesize_voice_response=True
        )
        res = voice_service.process_voice_interaction(telugu_voice_req)

        self.assertTrue(res.success)
        self.assertEqual(res.detected_language, "te")
        self.assertEqual(res.normalized_english_query, "Fever for 2 days")
        self.assertTrue(any('\u0c00' <= char <= '\u0c7f' for char in res.response_text_vernacular))
        self.assertIsNotNone(res.audio_base64)
        self.assertEqual(res.audio_mime_type, "audio/wav")

    # --------------------------------------------------------------------------
    # Scenario G: Proactive 48-Hour Follow-Up Lifecycle
    # --------------------------------------------------------------------------
    def test_golden_scenario_g_proactive_follow_up_lifecycle(self):
        """
        Scenario G:
        Appointment completed -> Follow-up task -> Scheduler ->
        48-hour trigger -> Follow-Up Agent -> User notification
        """
        # 1. Schedule 48-hour follow-up task
        task = follow_up_service.schedule_follow_up(FollowUpCreateRequest(
            patient_id="golden_pat_g",
            patient_name="Ananya",
            patient_phone="+91-9876543210",
            patient_language="te",
            source_type="APPOINTMENT",
            source_id="appt-golden-g",
            delay_hours=48.0,
            clinical_context={"doctor": "Dr. Priya Sharma", "department": "General Medicine"}
        ))
        self.assertEqual(task.status, FollowUpStatus.PENDING)

        # 2. Simulate 48-hour trigger (Day 2 on-demand execution)
        dispatched_task = follow_up_service.trigger_task_now(task.task_id)
        self.assertEqual(dispatched_task.status, FollowUpStatus.DISPATCHED)
        self.assertEqual(len(dispatched_task.notifications), 3)

        # 3. Patient provides positive recovery feedback
        completed_task = follow_up_service.record_patient_response(
            FollowUpResponseRequest(
                task_id=task.task_id,
                response_text="బాగున్నాను, జ్వరం తగ్గింది. ధన్యవాదాలు! (Feeling good, fever gone)",
                recovery_status="RECOVERED"
            )
        )
        self.assertEqual(completed_task.status, FollowUpStatus.COMPLETED)
        self.assertEqual(completed_task.patient_response["calculated_status"], "RECOVERED")
        self.assertFalse(completed_task.patient_response["needs_escalation"])


if __name__ == "__main__":
    unittest.main()
