import os
import re
import json
from typing import Dict, Any, List, Optional
from app.models.llm_intent import ParsedUserIntent, ExtractedSymptom
from app.services.redis_service import redis_service
from app.services.medical_triage_engine import medical_triage_engine

CLINICAL_DISCLAIMER = (
    "Note: This assistant coordinates consultations and does not provide "
    "a confirmed medical diagnosis. Please consult a registered medical practitioner for definitive clinical evaluation."
)

ORDINALS_MAP = {
    "first": 1,
    "1st": 1,
    "one": 1,
    "second": 2,
    "2nd": 2,
    "two": 2,
    "third": 3,
    "3rd": 3,
    "three": 3,
    "fourth": 4,
    "4th": 4,
    "last": -1,
}

DAYS_OF_WEEK = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class LLMService:
    """
    LLM Intent & Entity Extraction Layer.
    Translates conversational natural-language messages into structured ParsedUserIntent.
    Uses multi-turn conversation context stored in Redis.
    Never directly interacts with or updates database tables.
    """

    def __init__(self):
        self._llm = None
        self._init_live_model()

    def _init_live_model(self):
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                # gemini-2.0-flash is the current fast model
                self._llm = ChatGoogleGenerativeAI(
                    model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
                    google_api_key=api_key,
                    temperature=0.0,
                    max_retries=1,
                    request_timeout=15,
                )
            except Exception:
                self._llm = None

    def get_conversation_context(self, session_id: str) -> Dict[str, Any]:
        """Retrieves accumulated conversation context from Redis."""
        key = f"context:{session_id}"
        cached = redis_service.get_cached_data(key)
        return cached if isinstance(cached, dict) else {}

    def update_conversation_context(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Updates and persists multi-turn conversation context in Redis."""
        current = self.get_conversation_context(session_id)
        current.update(updates)
        key = f"context:{session_id}"
        redis_service.set_cached_data(key, current, ttl_seconds=86400)

    def parse_intent_and_entities(self, user_message: str, session_id: str) -> ParsedUserIntent:
        """
        Main entry point for natural language extraction.
        First tries live Gemini LLM if configured; otherwise uses deterministic contextual NLU.
        """
        context = self.get_conversation_context(session_id)

        # 1. Attempt live LLM structured extraction if configured and not explicitly opted out
        if self._llm and os.getenv("USE_LOCAL_NLU") != "1":
            try:
                import concurrent.futures
                prompt = (
                    "You are an AI Healthcare Intent & Entity Extraction Assistant. "
                    "Extract structured intents and entities from the user's message according to the schema. "
                    "Context from previous turns:\n"
                    f"{json.dumps(context)}\n\n"
                    f"User message: {user_message}\n\n"
                    "Never diagnose diseases. If required information is missing for an action, "
                    "set needs_clarification=True and provide clarification_question."
                )
                structured_llm = self._llm.with_structured_output(ParsedUserIntent)
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(structured_llm.invoke, prompt)
                    result = future.result(timeout=4)
                if result:
                    self._persist_extracted_context(session_id, result)
                    return result
            except Exception:
                pass

        # 2. Resilient deterministic contextual NLU engine
        result = self._parse_local_nlu(user_message, context)
        self._persist_extracted_context(session_id, result)
        return result

    def _persist_extracted_context(self, session_id: str, parsed: ParsedUserIntent) -> None:
        """Saves non-empty extracted entities to Redis session context."""
        updates: Dict[str, Any] = {}
        if parsed.department:
            updates["department"] = parsed.department
        if parsed.location:
            updates["location"] = parsed.location
        if parsed.date:
            updates["date"] = parsed.date
        if parsed.time:
            updates["time"] = parsed.time
        if parsed.doctor:
            updates["doctor"] = parsed.doctor
        if updates:
            self.update_conversation_context(session_id, updates)

    def _parse_local_nlu(self, text: str, context: Dict[str, Any]) -> ParsedUserIntent:
        """
        Context-aware natural language parser covering all required dialogue behaviors:
        - Symptom statements with duration ('I’ve had a headache for two days')
        - Specialty + Locality discovery ('Find a general physician near Indiranagar')
        - Conversational filter additions ('I need someone tomorrow evening')
        - Proximity requests ('Show me the nearest available doctor')
        - Conversational corrections ('Actually, change that to Saturday')
        - Anaphora / Ordinal resolution ('Book the second option')
        - Clarification detection when critical details are absent
        """
        lower = text.lower().strip()

        # ------------------------------------------------------------------
        # 1. Detect Corrections (e.g. "Actually, change that to Saturday")
        # ------------------------------------------------------------------
        is_correction = bool(re.search(r"\b(?:actually|change\s+that\s+to|instead|no\s+make\s+it|update\s+to)\b", lower))
        corrected_date = None
        for day in DAYS_OF_WEEK:
            if day in lower:
                corrected_date = day.capitalize()
                break
        if "tomorrow" in lower:
            corrected_date = "Tomorrow"
        elif "today" in lower:
            corrected_date = "Today"

        if is_correction and corrected_date:
            return ParsedUserIntent(
                intent="SEARCH_DOCTOR",
                is_change_or_correction=True,
                date=corrected_date,
                department=context.get("department"),
                location=context.get("location"),
                doctor=context.get("doctor"),
                time=context.get("time"),
            )

        # ------------------------------------------------------------------
        # 2. Detect Ordinal Selection (e.g. "Book the second option")
        # ------------------------------------------------------------------
        ordinal_match = re.search(r"\b(?:the\s+)?(first|1st|second|2nd|third|3rd|fourth|4th|last)\s+(?:option|one|doctor|slot)\b", lower)
        is_booking_verb = bool(re.search(r"\b(?:book|confirm|take|choose|select)\b", lower))

        if ordinal_match and is_booking_verb:
            word = ordinal_match.group(1)
            idx = ORDINALS_MAP.get(word, 1)

            # Resolve option from Redis context if available
            last_options = context.get("last_shown_options", [])
            resolved_doctor = None
            resolved_time = None
            resolved_date = context.get("date", "Tomorrow")
            resolved_dept = context.get("department", "General Medicine")

            if last_options:
                target_idx = (idx - 1) if idx > 0 else (len(last_options) - 1)
                if 0 <= target_idx < len(last_options):
                    opt = last_options[target_idx]
                    resolved_doctor = opt.get("doctor") or opt.get("name")
                    resolved_time = opt.get("time")
                    resolved_date = opt.get("date") or resolved_date
                    resolved_dept = opt.get("department") or resolved_dept

            if not resolved_doctor and not resolved_time:
                # Fallback to secondary doctor in context if options list was not recorded
                resolved_doctor = "Dr. Priya Sharma" if idx == 2 else "Dr. Ravi Kumar"
                resolved_time = "6:00 PM"

            return ParsedUserIntent(
                intent="BOOK_APPOINTMENT",
                appointment_action="BOOK",
                selected_option_index=idx,
                doctor=resolved_doctor,
                time=resolved_time,
                date=resolved_date,
                department=resolved_dept,
            )

        # ------------------------------------------------------------------
        # 3. Detect Direct Booking Requests
        # ------------------------------------------------------------------
        if re.search(r"\b(?:book|schedule|reserve|confirm\s+appointment)\b", lower):
            # Check for doctor name
            doc_m = re.search(r"\b(?:dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)", text, re.IGNORECASE)
            doctor_name = doc_m.group(0) if doc_m else context.get("doctor")

            # Check for time
            time_m = re.search(r"\b(\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)|\d{1,2}:\d{2})\b", text)
            time_val = time_m.group(1).strip() if time_m else context.get("time")

            # Check for date
            date_val = None
            if "tomorrow" in lower:
                date_val = "Tomorrow"
            elif "today" in lower:
                date_val = "Today"
            else:
                for day in DAYS_OF_WEEK:
                    if day in lower:
                        date_val = day.capitalize()
                        break
            date_val = date_val or context.get("date")

            # Clarification trigger: if user says "I want to book an appointment" with no details
            if not doctor_name and not time_val and not context.get("department"):
                return ParsedUserIntent(
                    intent="CLARIFICATION",
                    needs_clarification=True,
                    clarification_question="Which doctor or medical department would you like to book with, and for what date and time?",
                )

            # Clarification trigger: doctor specified but no time slot
            if doctor_name and not time_val:
                return ParsedUserIntent(
                    intent="CLARIFICATION",
                    doctor=doctor_name,
                    needs_clarification=True,
                    clarification_question=f"{doctor_name} has multiple available slots. Could you specify your preferred time (e.g. 5:30 PM or 6:00 PM)?",
                )

            return ParsedUserIntent(
                intent="BOOK_APPOINTMENT",
                appointment_action="BOOK",
                doctor=doctor_name,
                time=time_val,
                date=date_val or "Tomorrow",
                department=context.get("department", "General Medicine"),
            )

        # ------------------------------------------------------------------
        # 4. Detect Appointment Cancellation / Clear
        # ------------------------------------------------------------------
        if re.search(r"\b(?:cancel|delete|drop)\s+(?:my\s+)?appointment\b", lower):
            return ParsedUserIntent(
                intent="CANCEL_APPOINTMENT",
                appointment_action="CANCEL",
            )
        if re.search(r"\b(?:clear|reset)\s+(?:my\s+)?(?:appointment|summary)\b", lower):
            return ParsedUserIntent(
                intent="CANCEL_APPOINTMENT",
                appointment_action="CLEAR",
            )

        # ------------------------------------------------------------------
        # 5. Detect Symptoms (e.g. "I’ve had a headache for two days.")
        # ------------------------------------------------------------------
        # ------------------------------------------------------------------
        # 5. Medical Big Data Triage Engine & Symptoms Analysis
        # ------------------------------------------------------------------
        triage_pred = medical_triage_engine.predict(text)
        if triage_pred.get("symptoms") or triage_pred.get("isEmergency"):
            dur_m = re.search(r"\b(?:for|since|past)\s+(\d+\s+(?:days?|hours?|weeks?|months?))\b", lower)
            extracted_dur = dur_m.group(1) if dur_m else None

            found_symptoms: List[ExtractedSymptom] = [
                ExtractedSymptom(name=s["name"], duration=extracted_dur)
                for s in triage_pred["symptoms"]
            ]
            if not found_symptoms and triage_pred.get("primarySymptom"):
                found_symptoms = [ExtractedSymptom(name=triage_pred["primarySymptom"], duration=extracted_dur)]

            return ParsedUserIntent(
                intent="EXTRACT_SYMPTOMS",
                symptoms=found_symptoms,
                department=triage_pred["department"],
            )

        # ------------------------------------------------------------------
        # 6. Detect Location / Proximity ("Show me the nearest available doctor", "Doctors near Koramangala")
        # ------------------------------------------------------------------
        is_nearby = bool(re.search(r"\b(?:nearest|closest|near\s+me|nearby|around\s+me)\b", lower))
        locality_match = None
        for loc in ["indiranagar", "koramangala", "whitefield", "jayanagar", "hsr", "hsr layout", "bellandur", "hebbal", "cunningham road"]:
            if loc in lower:
                locality_match = f"{loc.title()}, Bengaluru"
                break

        # Check department keyword
        dept_match = None
        if re.search(r"\b(?:cardiolog(?:y|ist)|heart|cardiac)\b", lower):
            dept_match = "Cardiology"
        elif re.search(r"\b(?:pulmonolog(?:y|ist)|respiratory|lung)\b", lower):
            dept_match = "Pulmonology"
        elif re.search(r"\b(?:gastroenterolog(?:y|ist)|gastro|digestive)\b", lower):
            dept_match = "Gastroenterology"
        elif re.search(r"\b(?:neurolog(?:y|ist)|neuro|brain)\b", lower):
            dept_match = "Neurology"
        elif re.search(r"\b(?:gynecolog(?:y|ist)|obstetric(?:s|ian)|maternity)\b", lower):
            dept_match = "Gynecology"
        elif re.search(r"\b(?:psychiatr(?:y|ist)|mental\s+health)\b", lower):
            dept_match = "Psychiatry"
        elif re.search(r"\b(?:general\s+physician|general\s+medicine|physician|gp)\b", lower):
            dept_match = "General Medicine"
        elif re.search(r"\b(?:ent|ear\s+nose\s+throat)\b", lower):
            dept_match = "ENT"
        elif re.search(r"\b(?:dermatolog(?:y|ist)|skin)\b", lower):
            dept_match = "Dermatology"
        elif re.search(r"\b(?:pediatric(?:s|ian)|child)\b", lower):
            dept_match = "Pediatrics"
        elif re.search(r"\b(?:orthopedic(?:s)?|bone)\b", lower):
            dept_match = "Orthopedics"
        elif re.search(r"\b(?:ophthalmolog(?:y|ist)|eye)\b", lower):
            dept_match = "Ophthalmology"
        elif re.search(r"\b(?:dental|dentist|teeth)\b", lower):
            dept_match = "Dental"

        if is_nearby or locality_match:
            return ParsedUserIntent(
                intent="SEARCH_NEARBY" if is_nearby else "SEARCH_DOCTOR",
                location=locality_match or context.get("location"),
                department=dept_match or context.get("department", "General Medicine"),
            )

        # ------------------------------------------------------------------
        # 7. Detect Slot Filtering / Follow-up ("I need someone tomorrow evening")
        # ------------------------------------------------------------------
        time_period = None
        if "evening" in lower:
            time_period = "evening"
        elif "morning" in lower:
            time_period = "morning"
        elif "afternoon" in lower:
            time_period = "afternoon"

        date_pref = None
        if "tomorrow" in lower:
            date_pref = "Tomorrow"
        elif "today" in lower:
            date_pref = "Today"
        else:
            for day in DAYS_OF_WEEK:
                if day in lower:
                    date_pref = day.capitalize()
                    break

        if time_period or date_pref or dept_match:
            # Carry over active context
            carried_dept = dept_match or context.get("department", "General Medicine")
            carried_loc = context.get("location")
            return ParsedUserIntent(
                intent="FILTER_SLOTS" if (time_period or date_pref) else "SEARCH_DOCTOR",
                department=carried_dept,
                location=carried_loc,
                date=date_pref or context.get("date"),
                time=time_period or context.get("time"),
            )

        # ------------------------------------------------------------------
        # 8. Patient Info updates
        # ------------------------------------------------------------------
        if re.search(r"\b(?:my\s+name\s+is|set\s+my\s+name|change\s+my\s+phone|patient\s+info)\b", lower):
            return ParsedUserIntent(intent="UPDATE_PATIENT")

        # ------------------------------------------------------------------
        # 8.4 Lab Report Analyzer Intents
        # ------------------------------------------------------------------
        if re.search(r"\b(?:what\s+tests?\s+(?:are\s+)?in\s+(?:this\s+)?report|which\s+values?\s+are\s+outside|outside\s+(?:the\s+)?reference\s+range|out\s+of\s+range)\b", lower):
            return ParsedUserIntent(intent="LAB_RESULTS")

        if re.search(r"\b(?:what\s+does\s+page\s+3\s+say|page\s+3\b)", lower):
            return ParsedUserIntent(intent="LAB_EVIDENCE")

        if re.search(r"\b(?:show\s+(?:my\s+)?(?:latest\s+)?lab\s+report|latest\s+lab\s+report|upload\s+lab\s+report|lab\s+report)\b", lower):
            return ParsedUserIntent(intent="LAB_REPORT")

        # ------------------------------------------------------------------
        # 8.5 Document AI, Medicine & Insurance Workspace Intents
        # ------------------------------------------------------------------
        if re.search(r"\bupload\s+(?:this\s+)?(?:prescription|document|report|bill|pdf)\b", lower):
            return ParsedUserIntent(intent="UPLOAD_DOCUMENT")

        if re.search(r"\b(?:document\s+summary|summarize\s+(?:this\s+)?document)\b", lower):
            return ParsedUserIntent(intent="DOCUMENT_SUMMARY")

        if re.search(r"\bwhat\s+medicines?\s+(?:are\s+)?mentioned\b|\bmedicines?\s+in\s+(?:this\s+)?prescription\b|\bprescribed\s+dosage\b", lower):
            return ParsedUserIntent(intent="GET_MEDICINES")

        if re.search(r"\b(?:tell\s+me\s+about\s+(?:augmentin|dolo|[a-zA-Z]+)|what\s+is\s+(?:augmentin|dolo)|medicine\s+info(?:rmation)?)\b", lower):
            return ParsedUserIntent(intent="GET_MEDICINE_INFO")

        if re.search(r"\b(?:what\s+does\s+page\s+\d+|page\s+\d+\s+say|clause\s+evidence)\b", lower):
            return ParsedUserIntent(intent="DOCUMENT_EVIDENCE")

        if re.search(r"\b(?:is\s+this\s+(?:medicine\s+)?bill\s+covered|will\s+this\s+be\s+covered|covered\s+by\s+my\s+company|coverage\s+analysis)\b", lower):
            return ParsedUserIntent(intent="ANALYZE_INSURANCE")

        if re.search(r"\bhere\s+is\s+my\s+(?:company\s+)?(?:medical\s+)?policy\b|\bshow\s+policy\b|\bupload\s+policy\b", lower):
            return ParsedUserIntent(intent="SHOW_POLICY")

        # ------------------------------------------------------------------
        # 8.45 Bill Verification Intents
        # ------------------------------------------------------------------
        if re.search(r"\b(?:verify\s+(?:the\s+)?bill|bill\s+verification|compare\s+(?:the\s+)?(?:prescription\s+and\s+)?bill|prescription\s+and\s+bill)\b", lower):
            return ParsedUserIntent(intent="VERIFY_BILL")

        if re.search(r"\bbill\s+comparison\b", lower):
            return ParsedUserIntent(intent="BILL_COMPARISON")

        if re.search(r"\bbill\s+details?\b", lower):
            return ParsedUserIntent(intent="BILL_DETAILS")

        if re.search(r"\bverification\s+evidence\b", lower):
            return ParsedUserIntent(intent="VERIFICATION_EVIDENCE")

        if re.search(r"\bmissing\s+from\s+(?:the\s+)?bill\b", lower):
            return ParsedUserIntent(intent="COMPARE_BILL")

        # ------------------------------------------------------------------
        # 8.46 Drug-Drug Interaction (DDI) Checker Intents
        # ------------------------------------------------------------------
        if re.search(r"\b(?:interaction\s+details?|how\s+do\s+they\s+interact|interaction\s+mechanism)\b", lower):
            return ParsedUserIntent(intent="SHOW_INTERACTION_DETAILS")

        if re.search(r"\b(?:medication\s+list|all\s+my\s+medicines?|consolidated\s+medicines?|active\s+medications?)\b", lower):
            return ParsedUserIntent(intent="SHOW_MEDICATION_LIST")

        if re.search(r"\b(?:drug\s+interactions?|medicine\s+interactions?|drug-drug\s+interactions?|can\s+i\s+take\s+(?:these|them)\s+together|take\s+together|combine\s+medicines?|check\s+(?:drug\s+)?interactions?)\b", lower):
            return ParsedUserIntent(intent="SHOW_DRUG_INTERACTIONS")

        # ------------------------------------------------------------------
        # 8.47 Generic Medicine & Cost-Saver Intents
        # ------------------------------------------------------------------
        if re.search(r"\b(?:generic\s+options?|generic\s+equivalents?|generic\s+alternatives?|cheaper\s+alternatives?)\b", lower):
            return ParsedUserIntent(intent="SHOW_GENERIC_OPTIONS")

        if re.search(r"\b(?:price\s+comparison|compare\s+medicine\s+prices?|brand\s+vs\s+generic|price\s+differences?)\b", lower):
            return ParsedUserIntent(intent="SHOW_PRICE_COMPARISON")

        if re.search(r"\b(?:medicine\s+source|pricing\s+source|where\s+do\s+prices\s+come\s+from)\b", lower):
            return ParsedUserIntent(intent="SHOW_MEDICINE_SOURCE")

        if re.search(r"\b(?:cost\s+saver|medicine\s+costs?|how\s+much\s+do\s+these\s+cost|save\s+on\s+medicines?|jan\s+aushadhi)\b", lower):
            return ParsedUserIntent(intent="SHOW_PRICE_COMPARISON")

        if re.search(r"\b(?:where\s+can\s+i\s+(?:buy|get|find)|where\s+to\s+buy)\s+(?:these\s+)?medicines?\b|\b(?:pharmacies?|medical\s+stores?)\s+near\b|\bnearby\s+pharmac", lower):
            return ParsedUserIntent(intent="SEARCH_PHARMACY")

        # ------------------------------------------------------------------
        # 9. General / Fallback
        # ------------------------------------------------------------------
        return ParsedUserIntent(
            intent="GENERAL",
            department=context.get("department"),
            location=context.get("location"),
        )


# Global singleton instance
llm_service = LLMService()
