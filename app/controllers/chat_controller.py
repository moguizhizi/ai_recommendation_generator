# app/controllers/chat_controller.py

from fastapi import APIRouter, Request
from app.schemas.chat import AIRecPlanRequest, AIRecPlanResponse
from app.services.chat_service import generate_ai_plan
from llm.base import BaseLLM

router = APIRouter()


@router.post("/chat", response_model=AIRecPlanResponse)
def chat_api(req: AIRecPlanRequest, request: Request):
    # 从 app.state 里拿到全局 LLM
    llm: BaseLLM = request.app.state.llm

    # 传给业务层
    result = generate_ai_plan(req, llm)

    return AIRecPlanResponse(result=result)
