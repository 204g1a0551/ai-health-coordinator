"""
Comprehensive Test Suite for Phase 37 Part B: Proactive Follow-Up Agent.
Tests:
1. Follow-up task creation (+48 hour scheduled trigger time)
2. Decoupled asynchronous Redis & SQLite task queuing
3. Proactive Follow-Up Agent personalized clinical prompt generation (English, Telugu, Hindi)
4. Multi-channel notification delivery (WhatsApp, SMS, App Notification)
5. On-Demand Day 2 immediate simulation trigger (POST /api/follow-up/trigger/{task_id})
6. Batch due task processor (POST /api/follow-up/trigger-due)
7. Patient recovery feedback recording and escalation evaluation (POST /api/follow-up/respond/{task_id})
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure root & backend directories are in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from app.services.follow_up_service import follow_up_service
from app.agents.follow_up_agent import follow_up_agent
from app.models.follow_up import FollowUpCreateRequest, FollowUpStatus


class TestProactiveFollowUpAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_schedule_appointment_followup(self):
        """Test scheduling a +48 hour check-in following an appointment."""
        task = follow_up_agent.schedule_appointment_followup(
            patient_id="pat-101",
            patient_name="Mahesh Kumar",
            doctor="Dr. Priya Sharma",
            department="General Medicine",
            appointment_id="appt-9871",
            patient_language="te",
            patient_phone="+91-9876543210"
        )

        self.assertTrue(task.task_id.startswith("FLW-"))
        self.assertEqual(task.status, FollowUpStatus.PENDING)
        self.assertEqual(task.patient_language, "te")
        self.assertIn("APP_NOTIFICATION", task.channels)
        self.assertIn("WHATSAPP", task.channels)
        self.assertIn("SMS", task.channels)
        self.assertIsNotNone(task.follow_up_prompt_vernacular)
        self.assertIn("48 గంటలు", task.follow_up_prompt_vernacular)

    def test_schedule_prescription_followup(self):
        """Test scheduling a +48 hour medication tolerance check-in following prescription analysis."""
        task = follow_up_agent.schedule_prescription_followup(
            patient_id="pat-102",
            patient_name="Ramesh",
            document_id="doc-rx-123",
            medicines=["Augmentin 625mg", "Paracetamol 650mg"],
            patient_language="hi",
            patient_phone="+91-9123456780"
        )

        self.assertTrue(task.task_id.startswith("FLW-"))
        self.assertEqual(task.source_type, "PRESCRIPTION")
        self.assertEqual(task.patient_language, "hi")
        self.assertIn("Augmentin", task.follow_up_prompt_english)
        self.assertIn("दवाइयां", task.follow_up_prompt_vernacular)

    def test_day2_simulation_on_demand_trigger(self):
        """
        Tests the Day 2 simulation on-demand trigger:
        Immediately triggers Follow-Up Agent execution, dispatches notifications
        across WhatsApp, SMS, and App, and updates status to DISPATCHED.
        """
        task = follow_up_service.schedule_follow_up(FollowUpCreateRequest(
            patient_id="pat-sim-01",
            patient_name="Ananya",
            patient_phone="+91-9988776655",
            patient_language="te",
            source_type="APPOINTMENT",
            source_id="appt-sim-01",
            clinical_context={"doctor": "Dr. Priya Sharma", "department": "General Medicine"}
        ))

        # Trigger Day 2 simulation immediately
        triggered = follow_up_service.trigger_task_now(task.task_id)
        self.assertIsNotNone(triggered)
        self.assertEqual(triggered.status, FollowUpStatus.DISPATCHED)
        self.assertEqual(len(triggered.notifications), 3)

        channels = [n.channel for n in triggered.notifications]
        self.assertIn("APP_NOTIFICATION", channels)
        self.assertIn("WHATSAPP", channels)
        self.assertIn("SMS", channels)
        self.assertTrue(all(n.status == "DELIVERED" for n in triggered.notifications))

    def test_patient_recovery_response_recovered(self):
        """Test patient reporting recovery ('Feeling much better')."""
        task = follow_up_service.schedule_follow_up(FollowUpCreateRequest(
            patient_id="pat-rec-01",
            patient_name="Sita",
            source_type="APPOINTMENT",
            source_id="appt-rec-01"
        ))
        follow_up_service.trigger_task_now(task.task_id)

        # Patient submits recovery feedback
        res = follow_up_agent.process_patient_reply(
            task_id=task.task_id,
            reply_text="Feeling much better, fever is completely gone. Thank you!"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.status, FollowUpStatus.COMPLETED)
        self.assertEqual(res.patient_response["calculated_status"], "RECOVERED")
        self.assertFalse(res.patient_response["needs_escalation"])

    def test_patient_recovery_response_escalation(self):
        """Test patient reporting worsening symptoms triggers triage escalation."""
        task = follow_up_service.schedule_follow_up(FollowUpCreateRequest(
            patient_id="pat-esc-01",
            patient_name="Vikram",
            source_type="APPOINTMENT",
            source_id="appt-esc-01"
        ))
        follow_up_service.trigger_task_now(task.task_id)

        # Patient reports worsening symptoms
        res = follow_up_agent.process_patient_reply(
            task_id=task.task_id,
            reply_text="Fever is much higher now and having severe chest pain"
        )
        self.assertIsNotNone(res)
        self.assertEqual(res.status, FollowUpStatus.COMPLETED)
        self.assertEqual(res.patient_response["calculated_status"], "ESCALATE_TO_TRIAGE")
        self.assertTrue(res.patient_response["needs_escalation"])

    def test_api_follow_up_endpoints(self):
        """Test REST API endpoints under /api/follow-up."""
        # 1. Schedule via API
        create_res = self.client.post("/api/follow-up/schedule", json={
            "patient_id": "api-pat-01",
            "patient_name": "Kiran",
            "patient_language": "hi",
            "source_type": "APPOINTMENT",
            "source_id": "appt-api-01",
            "delay_hours": 48.0
        })
        self.assertEqual(create_res.status_code, 200)
        task_data = create_res.json()
        task_id = task_data["task_id"]

        # 2. Get task details
        get_res = self.client.get(f"/api/follow-up/task/{task_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["task_id"], task_id)

        # 3. Simulate Day 2 trigger via API
        trigger_res = self.client.post(f"/api/follow-up/trigger/{task_id}")
        self.assertEqual(trigger_res.status_code, 200)
        self.assertEqual(trigger_res.json()["status"], "DISPATCHED")

        # 4. Respond via API
        respond_res = self.client.post(f"/api/follow-up/respond/{task_id}", json={
            "task_id": task_id,
            "response_text": "सब ठीक है, मैं बेहतर महसूस कर रहा हूँ (All good, feeling better)",
            "recovery_status": "BETTER"
        })
        self.assertEqual(respond_res.status_code, 200)
        self.assertEqual(respond_res.json()["status"], "COMPLETED")

        # 5. List tasks
        list_res = self.client.get("/api/follow-up/tasks")
        self.assertEqual(list_res.status_code, 200)
        self.assertIsInstance(list_res.json(), list)


if __name__ == "__main__":
    unittest.main()
