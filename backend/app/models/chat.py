from datetime import datetime
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Message sent by the user")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="Reply from the assistant")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
