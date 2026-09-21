"""
Pydantic Models for Multilingual Voice Agent.
Supports STT, Language Detection, Translation/Normalization, and TTS.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class STTRequest(BaseModel):
    audio_base64: Optional[str] = Field(None, description="Base64 encoded audio payload")
    audio_format: str = Field("wav", description="Audio container format: wav, webm, mp3, ogg")
    sample_rate: int = Field(16000, description="Sampling rate in Hz")
    preferred_language: Optional[str] = Field(None, description="Optional language hint (e.g. te, hi, en)")


class STTResponse(BaseModel):
    success: bool = True
    transcription: str = Field(..., description="Recognized speech text")
    confidence: float = Field(0.95, description="Confidence score between 0 and 1")
    detected_language: str = Field("en", description="Detected language code")
    duration_seconds: float = Field(0.0, description="Audio duration in seconds")


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize into speech")
    language: str = Field("en", description="Target language code (te, hi, en, kn, ta, etc.)")
    voice_gender: str = Field("female", description="Voice gender: female or male")
    speech_rate: float = Field(1.0, description="Speech rate multiplier")


class TTSResponse(BaseModel):
    success: bool = True
    audio_base64: str = Field(..., description="Synthesized audio as Base64 string")
    audio_format: str = Field("audio/wav", description="MIME type of returned audio")
    duration_seconds: float = Field(1.0, description="Estimated audio duration")
    language: str = Field("en", description="Language used for synthesis")


class TranslationRequest(BaseModel):
    text: str = Field(..., description="Source text to translate and normalize")
    source_language: Optional[str] = Field(None, description="Source language if known (auto-detected if None)")
    target_language: str = Field("en", description="Target language code")
    clinical_normalization: bool = Field(True, description="Whether to extract standardized clinical symptoms")


class TranslationResponse(BaseModel):
    original_text: str
    source_language: str
    target_language: str
    translated_text: str
    normalized_clinical_query: str = Field(..., description="Standardized English clinical query for Triage/Agents")
    extracted_symptoms: List[str] = Field(default_factory=list, description="Extracted clinical symptoms")
    is_red_flag: bool = Field(False, description="Whether clinical symptoms match emergency red flags")


class VoiceProcessRequest(BaseModel):
    session_id: str = Field("default", description="Active conversation session ID")
    audio_base64: Optional[str] = Field(None, description="Raw spoken audio payload")
    text: Optional[str] = Field(None, description="Spoken transcript if STT was performed client-side")
    audio_format: str = Field("wav", description="Audio format")
    preferred_language: Optional[str] = Field(None, description="Selected language preference (auto, te, hi, en)")
    synthesize_voice_response: bool = Field(True, description="Whether to synthesize audio response in patient's language")


class VoiceProcessResponse(BaseModel):
    success: bool = True
    session_id: str
    original_transcript: str = Field(..., description="Original transcribed words in patient's language")
    detected_language: str = Field(..., description="Detected language code (te, hi, en, etc.)")
    language_name: str = Field(..., description="Human-readable language name (Telugu, Hindi, English)")
    normalized_english_query: str = Field(..., description="Standardized clinical query passed to Supervisor")
    response_text_english: str = Field(..., description="Primary clinical response from agents in English")
    response_text_vernacular: str = Field(..., description="Translated clinical response in patient's native tongue")
    audio_base64: Optional[str] = Field(None, description="Synthesized TTS speech audio in patient's language")
    audio_mime_type: Optional[str] = Field("audio/wav", description="MIME type of speech response")
    triage_status: Optional[str] = None
    normal_workflow_allowed: bool = True
    actions: List[Dict[str, Any]] = Field(default_factory=list)
