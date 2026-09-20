from fastapi import APIRouter
from app.models.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def handle_chat_message(request: ChatRequest) -> ChatResponse:
    """Handle incoming user message and return an initial greeting or starter reply."""
    user_msg = request.message.strip().lower()

    if not user_msg:
        reply = "Hello! Please describe your symptoms or health concern so I can assist you."
    elif any(greeting in user_msg for greeting in ["hello", "hi", "hey"]):
        reply = "Hello, how can I help you? Please describe any symptoms you are experiencing or what kind of appointment you need."
    else:
        reply = (
            "Hello, how can I help you? I received your message: "
            f"\"{request.message.strip()}\". Our multi-agent triage system will soon process this."
        )

    return ChatResponse(reply=reply)
