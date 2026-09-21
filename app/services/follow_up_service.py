"""
Proactive Follow-Up Scheduler & Multi-Channel Notification Service.
Runs decoupled from synchronous chat requests.
Handles:
Appointment / Prescription -> Create Follow-Up Task -> Redis / SQLite Scheduler ->
48 Hours Later (or On-Demand Trigger) -> Follow-Up Agent -> Patient Notification (WhatsApp, SMS, App).
"""

import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from app.models.follow_up import (
    FollowUpTask,
    FollowUpNotification,
    FollowUpStatus,
    FollowUpCreateRequest,
    FollowUpResponseRequest,
)
from app.services.redis_service import redis_service
from app.services.language_service import language_service
from app.db.repository import get_db_connection, init_db

logger = logging.getLogger("follow_up_service")


class FollowUpService:
    """
    Asynchronous Follow-Up Queue & Notification Engine.
    Coordinates 48-hour post-consultation and medication check-in workflows.
    """

    def __init__(self):
        init_db()

    def schedule_follow_up(self, request: FollowUpCreateRequest) -> FollowUpTask:
        """
        Creates a scheduled follow-up task (+48 hours by default) in Redis and SQLite.
        """
        now = datetime.utcnow()
        trigger_time = now + timedelta(hours=request.delay_hours)

        task_id = f"FLW-{uuid.uuid4().hex[:8].upper()}"
        created_at_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        trigger_at_str = trigger_time.strftime("%Y-%m-%dT%H:%M:%SZ")

        lang = request.patient_language or "en"
        context = request.clinical_context or {}

        # Construct initial follow-up message in English & Vernacular
        prompt_en, prompt_vernacular = self._build_follow_up_prompts(
            source_type=request.source_type,
            patient_name=request.patient_name or "Patient",
            context=context,
            lang=lang
        )

        task = FollowUpTask(
            task_id=task_id,
            patient_id=request.patient_id,
            patient_name=request.patient_name or "Patient",
            patient_phone=request.patient_phone or "+91-9876543210",
            patient_language=lang,
            source_type=request.source_type,
            source_id=request.source_id,
            created_at=created_at_str,
            trigger_at=trigger_at_str,
            status=FollowUpStatus.PENDING,
            channels=["APP_NOTIFICATION", "SMS", "WHATSAPP"],
            clinical_context=context,
            follow_up_prompt_english=prompt_en,
            follow_up_prompt_vernacular=prompt_vernacular,
            notifications=[]
        )

        # 1. Store in SQLite
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO follow_up_tasks (
                    task_id, patient_id, patient_name, patient_phone, patient_language,
                    source_type, source_id, created_at, trigger_at, status,
                    channels_json, clinical_context_json,
                    follow_up_prompt_english, follow_up_prompt_vernacular, patient_response_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.patient_id, task.patient_name, task.patient_phone, task.patient_language,
                task.source_type, task.source_id, task.created_at, task.trigger_at, task.status.value,
                json.dumps(task.channels), json.dumps(task.clinical_context),
                task.follow_up_prompt_english, task.follow_up_prompt_vernacular, None
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error("Failed to persist follow-up task to DB: %s", str(e))

        # 2. Store in Redis
        try:
            redis_service.set_cached_data(f"follow_up:{task_id}", task.dict(), ttl=86400 * 7)
        except Exception:
            pass

        return task

    def trigger_task_now(self, task_id: str) -> Optional[FollowUpTask]:
        """
        Executes the Follow-Up Agent for a specific task immediately.
        Simulates the 48-Hour / Day 2 trigger on demand.
        Dispatches multi-channel notifications (WhatsApp, SMS, App).
        """
        task = self.get_task_by_id(task_id)
        if not task:
            return None

        # Build personalized clinical inquiry
        prompt_en, prompt_vernacular = self._build_follow_up_prompts(
            source_type=task.source_type,
            patient_name=task.patient_name,
            context=task.clinical_context,
            lang=task.patient_language
        )

        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        dispatched_notifications = []

        # Multi-Channel Dispatch
        for channel in task.channels:
            notif_id = f"NOTIF-{uuid.uuid4().hex[:6].upper()}"
            notif = FollowUpNotification(
                notification_id=notif_id,
                channel=channel,
                recipient=task.patient_phone if channel in ["SMS", "WHATSAPP"] else task.patient_id,
                message=prompt_vernacular if task.patient_language != "en" else prompt_en,
                language=task.patient_language,
                dispatched_at=now_str,
                status="DELIVERED",
                delivery_metadata={
                    "gateway": f"telecom_{channel.lower()}_simulator",
                    "channel_priority": "HIGH",
                    "delivery_latency_ms": 42
                }
            )
            dispatched_notifications.append(notif)

            # Record in SQLite
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO follow_up_notifications (
                        notification_id, task_id, channel, recipient, message,
                        language, dispatched_at, status, delivery_metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    notif.notification_id, task_id, notif.channel, notif.recipient,
                    notif.message, notif.language, notif.dispatched_at, notif.status,
                    json.dumps(notif.delivery_metadata)
                ))
                conn.commit()
                conn.close()
            except Exception:
                pass

        # Update task state
        task.status = FollowUpStatus.DISPATCHED
        task.follow_up_prompt_english = prompt_en
        task.follow_up_prompt_vernacular = prompt_vernacular
        task.notifications = dispatched_notifications

        # Update DB & Redis
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE follow_up_tasks
                SET status = ?, follow_up_prompt_english = ?, follow_up_prompt_vernacular = ?
                WHERE task_id = ?
            """, (task.status.value, task.follow_up_prompt_english, task.follow_up_prompt_vernacular, task_id))
            conn.commit()
            conn.close()
        except Exception:
            pass

        try:
            redis_service.set_cached_data(f"follow_up:{task_id}", task.dict(), ttl=86400 * 7)
        except Exception:
            pass

        return task

    def trigger_due_followups(self) -> List[FollowUpTask]:
        """
        Batch scheduler worker: Checks all tasks whose trigger_at has arrived and executes them.
        """
        now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        dispatched_tasks = []

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT task_id FROM follow_up_tasks
                WHERE trigger_at <= ? AND status = 'PENDING'
            """, (now_str,))
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                tid = r["task_id"]
                t = self.trigger_task_now(tid)
                if t:
                    dispatched_tasks.append(t)
        except Exception as e:
            logger.error("Error querying due follow-up tasks: %s", str(e))

        return dispatched_tasks

    def record_patient_response(self, request: FollowUpResponseRequest) -> Optional[FollowUpTask]:
        """
        Records patient recovery feedback and analyzes whether clinical re-escalation is necessary.
        """
        task = self.get_task_by_id(request.task_id)
        if not task:
            return None

        # Analyze patient feedback
        lower = request.response_text.lower()
        if any(w in lower for w in ["better", "good", "fine", "recovered", "బాగున్నాను", "నయమైంది", "अच्छा", "ठीक"]):
            status_calc = "RECOVERED"
            needs_escalation = False
        elif any(w in lower for w in ["worse", "severe", "chest pain", "fever higher", "బాధగా ఉంది", "నొప్పి ఎక్కువైంది", "दर्द बढ़ गया"]):
            status_calc = "ESCALATE_TO_TRIAGE"
            needs_escalation = True
        else:
            status_calc = request.recovery_status or "STABLE"
            needs_escalation = False

        response_payload = {
            "patient_response_text": request.response_text,
            "received_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "calculated_status": status_calc,
            "needs_escalation": needs_escalation,
            "recommended_action": "Schedule immediate doctor callback" if needs_escalation else "Continue routine monitoring"
        }

        task.status = FollowUpStatus.COMPLETED
        task.patient_response = response_payload

        # Update SQLite
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE follow_up_tasks
                SET status = ?, patient_response_json = ?
                WHERE task_id = ?
            """, (task.status.value, json.dumps(response_payload), request.task_id))
            conn.commit()
            conn.close()
        except Exception:
            pass

        try:
            redis_service.set_cached_data(f"follow_up:{request.task_id}", task.dict(), ttl=86400 * 7)
        except Exception:
            pass

        return task

    def get_task_by_id(self, task_id: str) -> Optional[FollowUpTask]:
        """Retrieves task from Redis or SQLite."""
        # Try Redis
        try:
            cached = redis_service.get_cached_data(f"follow_up:{task_id}")
            if cached:
                return FollowUpTask(**cached)
        except Exception:
            pass

        # Try SQLite
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM follow_up_tasks WHERE task_id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            # Fetch notifications
            cursor.execute("SELECT * FROM follow_up_notifications WHERE task_id = ?", (task_id,))
            notif_rows = cursor.fetchall()
            conn.close()

            notifs = [
                FollowUpNotification(
                    notification_id=nr["notification_id"],
                    channel=nr["channel"],
                    recipient=nr["recipient"],
                    message=nr["message"],
                    language=nr["language"] or "en",
                    dispatched_at=nr["dispatched_at"],
                    status=nr["status"],
                    delivery_metadata=json.loads(nr["delivery_metadata_json"]) if nr["delivery_metadata_json"] else None
                ) for nr in notif_rows
            ]

            return FollowUpTask(
                task_id=row["task_id"],
                patient_id=row["patient_id"],
                patient_name=row["patient_name"],
                patient_phone=row["patient_phone"],
                patient_language=row["patient_language"] or "en",
                source_type=row["source_type"],
                source_id=row["source_id"],
                created_at=row["created_at"],
                trigger_at=row["trigger_at"],
                status=FollowUpStatus(row["status"]),
                channels=json.loads(row["channels_json"]) if row["channels_json"] else ["APP_NOTIFICATION"],
                clinical_context=json.loads(row["clinical_context_json"]) if row["clinical_context_json"] else {},
                follow_up_prompt_english=row["follow_up_prompt_english"],
                follow_up_prompt_vernacular=row["follow_up_prompt_vernacular"],
                notifications=notifs,
                patient_response=json.loads(row["patient_response_json"]) if row["patient_response_json"] else None
            )
        except Exception as e:
            logger.error("Error reading task from DB: %s", str(e))
            return None

    def list_tasks(
        self,
        patient_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[FollowUpTask]:
        """Lists follow-up tasks with optional patient_id and status filters."""
        tasks: List[FollowUpTask] = []
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = "SELECT task_id FROM follow_up_tasks WHERE 1=1"
            params = []
            if patient_id:
                query += " AND patient_id = ?"
                params.append(patient_id)
            if status:
                query += " AND status = ?"
                params.append(status.upper())
            query += " ORDER BY rowid DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                t = self.get_task_by_id(r["task_id"])
                if t:
                    tasks.append(t)
        except Exception:
            pass

        return tasks

    def _build_follow_up_prompts(
        self,
        source_type: str,
        patient_name: str,
        context: Dict[str, Any],
        lang: str
    ) -> Tuple[str, str]:
        """Builds tailored follow-up queries in English and the patient's native language."""
        doctor = context.get("doctor", "your physician")
        dept = context.get("department", "consultation")
        medicines = context.get("medicines", [])

        if source_type == "PRESCRIPTION" and medicines:
            med_names = ", ".join(medicines[:2])
            en_msg = (
                f"Hello {patient_name}, this is your AI Health Care Coordinator following up on your recent prescription. "
                f"How are you feeling now? Have you been able to start taking your prescribed medication ({med_names}) as directed? "
                "Please let us know if you have any questions or are experiencing any side effects."
            )
            te_msg = (
                f"నమస్కారం {patient_name} గారు, మీ ఇటీవల ప్రిస్క్రిప్షన్ గురించి ఏఐ హెల్త్ అసిస్టెంట్ ఫాలో-అప్. "
                f"ప్రస్తుతం మీ ఆరోగ్యం ఎలా ఉంది? డాక్టర్ సూచించిన మందులు ({med_names}) తీసుకోవడం ప్రారంభించారా? "
                "మీకు ఏవైనా ఇబ్బందులు లేదా లక్షణాలు ఉంటే దయచేసి మాకు తెలియజేయండి."
            )
            hi_msg = (
                f"नमस्ते {patient_name} जी, आपके हालिया पर्चे (प्रिस्क्रिप्शन) के संदर्भ में आपका एआई हेल्थ असिस्टेंट संपर्क कर रहा है। "
                f"अब आपकी तबीयत कैसी है? क्या आपने अपनी दवाइयां ({med_names}) डॉक्टर के निर्देशानुसार लेना शुरू कर दिया है? "
                "यदि कोई समस्या या साइड इफेक्ट्स महसूस हो रहे हों, तो कृपया हमें बताएं।"
            )
        else:
            en_msg = (
                f"Hello {patient_name}, it has been 48 hours since your appointment with {doctor} ({dept}). "
                "How are you feeling now? Has your condition improved? "
                "Reply here if you need a follow-up consultation or further assistance."
            )
            te_msg = (
                f"నమస్కారం {patient_name} గారు, డాక్టర్ {doctor} ({dept}) తో మీ అపాయింట్‌మెంట్ ముగిసి 48 గంటలు అయింది. "
                "ప్రస్తుతం మీ ఆరోగ్యం ఎలా ఉంది? లక్షణాలు తగ్గాయా? "
                "మీకు తదుపరి సంప్రదింపులు లేదా సహాయం అవసరమైతే ఇక్కడ తెలియజేయండి."
            )
            hi_msg = (
                f"नमस्ते {patient_name} जी, डॉक्टर {doctor} ({dept}) के साथ आपके अपॉइंटमेंट को 48 घंटे हो चुके हैं। "
                "अब आप कैसा महसूस कर रहे हैं? क्या आपके स्वास्थ्य में सुधार है? "
                "यदि आपको फॉलो-अप परामर्श या सहायता चाहिए, तो कृपया यहाँ उत्तर दें।"
            )

        vernacular = te_msg if lang == "te" else (hi_msg if lang == "hi" else en_msg)
        return en_msg, vernacular


follow_up_service = FollowUpService()
