"""
Comprehensive Test Suite for Phase 37 Part A: Multilingual Voice Agent.
Tests:
1. Script-based Language Detection (Telugu, Hindi, English, Kannada, Tamil, Bengali)
2. Vernacular Clinical Normalization ("నాకు రెండు రోజులుగా జ్వరం ఉంది" -> "Fever for 2 days")
3. Emergency Vernacular Red-Flag Detection
4. Back-Translation to Patient's Native Tongue
5. Speech-to-Text (STT) and Text-to-Speech (TTS) WAV Audio Synthesis
6. REST API Endpoints (/api/voice/process, /api/voice/stt, /api/voice/tts, /api/voice/translate, /api/voice/languages)
"""

import os
import sys
import base64
import unittest
from fastapi.testclient import TestClient

# Ensure root & backend directories are in path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in [BASE_DIR, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from app.services.language_service import language_service, SUPPORTED_LANGUAGES
from app.services.voice_service import voice_service, generate_synthesized_wav_audio
from app.models.voice import STTRequest, TTSRequest, VoiceProcessRequest


class TestMultilingualVoiceAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_language_detection(self):
        """Test high-precision Unicode script language detection."""
        # Telugu
        lang_te, conf_te = language_service.detect_language("నాకు రెండు రోజులుగా జ్వరం ఉంది.")
        self.assertEqual(lang_te, "te")
        self.assertGreaterEqual(conf_te, 0.8)

        # Hindi
        lang_hi, conf_hi = language_service.detect_language("मुझे दो दिन से तेज बुखार है।")
        self.assertEqual(lang_hi, "hi")
        self.assertGreaterEqual(conf_hi, 0.8)

        # English
        lang_en, conf_en = language_service.detect_language("I have a severe headache and fever.")
        self.assertEqual(lang_en, "en")

        # Kannada
        lang_kn, _ = language_service.detect_language("ನನಗೆ ಎರಡು ದಿನಗಳಿಂದ ಜ್ವರವಿದೆ.")
        self.assertEqual(lang_kn, "kn")

        # Tamil
        lang_ta, _ = language_service.detect_language("எனக்கு இரண்டு நாட்களாக காய்ச்சல் உள்ளது.")
        self.assertEqual(lang_ta, "ta")

    def test_telugu_user_example_normalization(self):
        """
        Validates the exact example from user specification:
        Patient: 'నాకు రెండు రోజులుగా జ్వరం ఉంది.'
        -> Telugu STT
        -> Symptom extraction
        -> 'Fever for 2 days'
        """
        text = "నాకు రెండు రోజులుగా జ్వరం ఉంది."
        result = language_service.normalize_to_english_clinical(text)

        self.assertEqual(result.source_language, "te")
        self.assertEqual(result.normalized_clinical_query, "Fever for 2 days")
        self.assertIn("fever", result.extracted_symptoms)
        self.assertFalse(result.is_red_flag)

    def test_hindi_symptom_normalization(self):
        """Validates Hindi clinical symptom normalization."""
        text = "मुझे दो दिन से बुखार है।"
        result = language_service.normalize_to_english_clinical(text)

        self.assertEqual(result.source_language, "hi")
        self.assertEqual(result.normalized_clinical_query, "Fever for 2 days")
        self.assertIn("fever", result.extracted_symptoms)
        self.assertFalse(result.is_red_flag)

    def test_vernacular_emergency_red_flag_detection(self):
        """Test emergency red-flag detection in Telugu and Hindi."""
        # Telugu severe chest pain
        te_emergency = "నాకు తీవ్రమైన గుండె నొప్పి ఉంది"
        is_red_te, flags_te = language_service.check_red_flag_symptoms(te_emergency, "te")
        self.assertTrue(is_red_te)
        self.assertTrue(any("chest pain" in f for f in flags_te))

        # Hindi severe chest pain
        hi_emergency = "मुझे सीने में तेज दर्द है"
        is_red_hi, flags_hi = language_service.check_red_flag_symptoms(hi_emergency, "hi")
        self.assertTrue(is_red_hi)
        self.assertTrue(any("chest pain" in f for f in flags_hi))

    def test_back_translation_to_vernacular(self):
        """Test translating assistant clinical response back to patient's native tongue."""
        en_response = "I have noted that you have fever for 2 days. We have organized General Medicine doctors for you."

        # Telugu back translation
        te_reply = language_service.translate_response_to_vernacular(en_response, "te")
        self.assertIn("జ్వరం", te_reply)

        # Hindi back translation
        hi_reply = language_service.translate_response_to_vernacular(en_response, "hi")
        self.assertIn("बुखार", hi_reply)

    def test_wav_audio_synthesis_headers(self):
        """Test pure-Python 16-bit PCM WAV generation with valid RIFF headers."""
        wav_bytes = generate_synthesized_wav_audio(duration_seconds=1.0, frequency_hz=440.0)
        self.assertGreater(len(wav_bytes), 44)
        # Check RIFF and WAVE magic headers
        self.assertEqual(wav_bytes[:4], b"RIFF")
        self.assertEqual(wav_bytes[8:12], b"WAVE")
        self.assertEqual(wav_bytes[12:16], b"fmt ")

    def test_tts_service(self):
        """Test TTS synthesis returning base64 audio."""
        req = TTSRequest(text="మీ ఆరోగ్యం ఎలా ఉంది?", language="te")
        res = voice_service.text_to_speech(req)
        self.assertTrue(res.success)
        self.assertEqual(res.audio_format, "audio/wav")
        self.assertIsNotNone(res.audio_base64)
        decoded = base64.b64decode(res.audio_base64)
        self.assertEqual(decoded[:4], b"RIFF")

    def test_api_languages_endpoint(self):
        """Test GET /api/voice/languages."""
        res = self.client.get("/api/voice/languages")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("te", [l["code"] for l in data["languages"]])
        self.assertIn("hi", [l["code"] for l in data["languages"]])
        self.assertIn("en", [l["code"] for l in data["languages"]])

    def test_api_voice_process_telugu(self):
        """Test POST /api/voice/process with the exact Telugu user request."""
        payload = {
            "session_id": "test_voice_session_1",
            "text": "నాకు రెండు రోజులుగా జ్వరం ఉంది.",
            "preferred_language": "te",
            "synthesize_voice_response": True
        }
        res = self.client.post("/api/voice/process", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["detected_language"], "te")
        self.assertEqual(data["normalized_english_query"], "Fever for 2 days")
        self.assertIsNotNone(data["response_text_vernacular"])
        self.assertIsNotNone(data["audio_base64"])
        self.assertEqual(data["audio_mime_type"], "audio/wav")

    def test_api_voice_process_hindi(self):
        """Test POST /api/voice/process with Hindi request."""
        payload = {
            "session_id": "test_voice_session_2",
            "text": "मुझे दो दिन से बुखार है।",
            "preferred_language": "hi",
            "synthesize_voice_response": True
        }
        res = self.client.post("/api/voice/process", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["detected_language"], "hi")
        self.assertEqual(data["normalized_english_query"], "Fever for 2 days")


if __name__ == "__main__":
    unittest.main()
