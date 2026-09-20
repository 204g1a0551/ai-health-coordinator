from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse, SessionMessage
from app.agents import health_graph

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# In-memory session store to maintain conversation history
SESSION_STORE: Dict[str, List[SessionMessage]] = {}


@router.post("", response_model=ChatResponse)
async def handle_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Handle incoming chat message via LangGraph Supervisor & Symptom Agent pipeline.
    Maintains session history and returns structured UI actions.
    """
    session_id = request.session_id.strip()
    user_text = request.message.strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    now_time = datetime.utcnow().strftime("%I:%M %p")

    # Initialize session history if new
    if session_id not in SESSION_STORE:
        SESSION_STORE[session_id] = []

    # Record user message in session history
    SESSION_STORE[session_id].append(
        SessionMessage(sender="user", text=user_text, timestamp=now_time)
    )

    # Invoke LangGraph coordinator
    initial_state = {
        "user_message": user_text,
        "session_id": session_id,
        "route": "",
        "symptoms": [],
        "actions": [],
        "final_response": "",
    }

    result_state = health_graph.invoke(initial_state)

    reply_text = result_state.get(
        "final_response",
        "I understand. I can help organize your symptoms and appointment request."
    )
    actions = result_state.get("actions", [])

    # Record assistant reply in session history
    SESSION_STORE[session_id].append(
        SessionMessage(sender="assistant", text=reply_text, timestamp=now_time)
    )

    return ChatResponse(
        message=reply_text,
        actions=actions,
        sessionId=session_id,
    )


@router.get("/history/{session_id}", response_model=List[SessionMessage])
async def get_session_history(session_id: str) -> List[SessionMessage]:
    """Retrieve full conversation history for a given session ID."""
    return SESSION_STORE.get(session_id.strip(), [])
