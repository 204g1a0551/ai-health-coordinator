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
    actions: List[Any] = Field(default_factory=list, description="Structured actions for future UI updates")
    session_id: Optional[str] = Field(default=None, alias="sessionId", description="Session ID")

    class Config:
        populate_by_name = True


class SessionMessage(BaseModel):
    sender: str
    text: str
    timestamp: str
