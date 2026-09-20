from datetime import datetime
from typing import Dict, List
from fastapi import APIRouter, HTTPException
from app.models.chat import ChatRequest, ChatResponse, SessionMessage
from app.agents import health_graph
from app.services.redis_service import redis_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def handle_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Handle incoming chat message via LangGraph Supervisor & Multi-Agent pipeline.
    Maintains session history and temporary state via Redis service layer.
    """
    session_id = request.session_id.strip()
    user_text = request.message.strip()

    if not user_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    now_time = datetime.utcnow().strftime("%I:%M %p")

    # Record user message in Redis session history
    user_msg_dict = {"sender": "user", "text": user_text, "timestamp": now_time}
    redis_service.save_chat_message(session_id, user_msg_dict)

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

    # Record assistant reply in Redis session history
    asst_msg_dict = {"sender": "assistant", "text": reply_text, "timestamp": now_time}
    redis_service.save_chat_message(session_id, asst_msg_dict)

    # Cache LangGraph state in Redis
    redis_service.save_agent_state(session_id, result_state)

    return ChatResponse(
        message=reply_text,
        actions=actions,
        sessionId=session_id,
    )


@router.get("/history/{session_id}", response_model=List[SessionMessage])
async def get_session_history(session_id: str) -> List[SessionMessage]:
    """Retrieve full conversation history for a given session ID from Redis."""
    raw_history = redis_service.get_chat_history(session_id.strip())
    return [SessionMessage(**msg) for msg in raw_history]
