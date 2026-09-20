from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse, SessionMessage

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# In-memory session store to maintain conversation history for each session/conversation ID
SESSION_STORE: Dict[str, List[SessionMessage]] = {}


@router.post("", response_model=ChatResponse)
async def handle_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Handle incoming chat message, track history per session,
    and return structured response with message and actions list.
    """
    session_id = request.session_id.strip()
    user_text = request.message.strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    now_iso = datetime.utcnow().strftime("%I:%M %p")

    # Initialize session history if new
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []

    # Record user message in session history
    user_msg_entry = SessionMessage(
        sender="user",
        text=user_text,
        timestamp=now_iso,
    )
    SESSION_STORE[session_id].append(user_msg_entry)

    # Generate assistant reply
    lower_text = user_text.lower()

    if any(k in lower_text for k in ["fever", "headache", "cough", "pain", "symptom", "cold"]):
        reply_text = "I understand. I can help organize your symptoms and appointment request."
    elif any(k in lower_text for k in ["hello", "hi", "hey"]):
        reply_text = "Hello! I am your AI Health Checkup & Appointment Coordinator. Please describe your symptoms or appointment needs."
    elif any(k in lower_text for k in ["book", "appointment", "doctor", "slot", "schedule"]):
        reply_text = "I can help you coordinate an appointment with the appropriate department and doctor."
    else:
        reply_text = "I understand. I can help organize your symptoms and appointment request."

    # Record assistant message in session history
    assistant_msg_entry = SessionMessage(
        sender="assistant",
        text=reply_text,
        timestamp=now_iso,
    )
    SESSION_STORE[session_id].append(assistant_msg_entry)

    return ChatResponse(
        message=reply_text,
        actions=[],
        sessionId=session_id,
    )


@router.get("/history/{session_id}", response_model=List[SessionMessage])
async def get_session_history(session_id: str) -> List[SessionMessage]:
    """Retrieve full conversation history for a given session ID."""
    return SESSION_STORE.get(session_id.strip(), [])
