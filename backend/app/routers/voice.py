"""
Multilingual Voice Agent Router.
Endpoints:
- POST /api/voice/process: End-to-end voice roundtrip (Audio/Text -> STT -> Normalization -> Triage -> Supervisor -> TTS)
- POST /api/voice/stt: Transcribe speech audio to text
- POST /api/voice/tts: Synthesize text to speech audio
- POST /api/voice/translate: Translate and normalize clinical symptoms
- GET /api/voice/languages: List supported languages
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from app.models.voice import (
    STTRequest,
    STTResponse,
    TTSRequest,
    TTSResponse,
    TranslationRequest,
    TranslationResponse,
    VoiceProcessRequest,
    VoiceProcessResponse,
)
from app.services.voice_service import voice_service
from app.services.language_service import language_service, SUPPORTED_LANGUAGES

router = APIRouter(prefix="/api/voice", tags=["Multilingual Voice Agent"])


@router.post("/process", response_model=VoiceProcessResponse)
async def process_voice_message(request: VoiceProcessRequest) -> VoiceProcessResponse:
    """
    Processes incoming spoken or text interaction through the Multilingual Voice Pipeline:
    1. Speech-to-Text (STT)
    2. Language Identification (Telugu, Hindi, English, etc.)
    3. Clinical Symptom Normalization
    4. Red-Flag Emergency Triage
    5. LangGraph Multi-Agent Supervisor
    6. Response Translation to Patient's Native Language
    7. Text-to-Speech (TTS) Speech Generation
    """
    try:
        return voice_service.process_voice_interaction(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(request: STTRequest) -> STTResponse:
    """Transcribes audio payload into text with language detection."""
    try:
        return voice_service.speech_to_text(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Speech recognition failed: {str(e)}")


@router.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest) -> TTSResponse:
    """Synthesizes text into high-fidelity speech audio (WAV) in patient's native tongue."""
    try:
        return voice_service.text_to_speech(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Speech synthesis failed: {str(e)}")


@router.post("/translate", response_model=TranslationResponse)
async def translate_and_normalize(request: TranslationRequest) -> TranslationResponse:
    """Normalizes natural vernacular phrasing into standardized English clinical symptoms."""
    try:
        return language_service.normalize_to_english_clinical(
            text=request.text,
            source_lang=request.source_language
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Translation failed: {str(e)}")


@router.get("/languages")
async def get_supported_languages() -> Dict[str, Any]:
    """Returns supported Indic and international languages and their speech recognition locales."""
    return {
        "count": len(SUPPORTED_LANGUAGES),
        "primary_languages": ["en", "te", "hi"],
        "extended_languages": ["kn", "ta", "ml", "mr", "bn"],
        "languages": list(SUPPORTED_LANGUAGES.values())
    }
