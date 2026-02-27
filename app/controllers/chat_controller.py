# app/controllers/chat_controller.py
from fastapi import APIRouter
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import chat

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat_api(req: ChatRequest):
    result = chat(req.prompt)
    return ChatResponse(result=result)