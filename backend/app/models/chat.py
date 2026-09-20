from typing import List, Any, Optional, Dict
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Message sent by the user")
    session_id: str = Field(..., alias="sessionId", description="Conversation / session ID")
    coordinates: Optional[Dict[str, float]] = Field(default=None, description="Optional user coordinates for nearby search")

    class Config:
        populate_by_name = True


class ChatResponse(BaseModel):
    message: str = Field(..., description="Reply text from the assistant")
    action: Optional[str] = Field(default=None, description="Primary controlled UI action (e.g. SHOW_SYMPTOMS, SHOW_SLOTS)")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Structured payload for the primary UI action")
    actions: List[Any] = Field(default_factory=list, description="Structured actions for UI updates")
    session_id: Optional[str] = Field(default=None, alias="sessionId", description="Session ID")

    class Config:
        populate_by_name = True



class SessionMessage(BaseModel):
    sender: str
    text: str
    timestamp: str
