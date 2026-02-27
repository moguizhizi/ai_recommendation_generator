# app/controllers/chat_controller.py
from fastapi import APIRouter
from app.schemas.chat import AIRecPlanRequest, AIRecPlanResponse
from app.services.chat_service import chat

router = APIRouter()

@router.post("/chat", response_model=AIRecPlanResponse)
def chat_api(req: AIRecPlanRequest):
    result = chat(req.prompt)
    return AIRecPlanResponse(result=result)