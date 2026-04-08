# app/controllers/chat_controller.py

import time
from typing import Any, Dict
from fastapi import APIRouter, Request
from app.schemas.chat import AIRecPlanRequest, AIRecPlanResponse
from app.services.chat_service import generate_ai_plan
from llm.base import BaseLLM

from utils.logger import get_logger
from models.model_factory import ModelManager

logger = get_logger(__name__)

router = APIRouter(tags=["chat-v1"])


@router.post("/chat", response_model=AIRecPlanResponse, deprecated=True)
def chat_api(req: AIRecPlanRequest, request: Request):

    llm: BaseLLM = request.app.state.llm
    score_model_manager: ModelManager = request.app.state.model_manager
    config: Dict[str, Any] = request.app.state.config

    start_time = time.time()

    logger.info(
        f"[CHAT_API_START] user_id={req.user_id} " f"patient_code={req.patient_code} "
    )

    result = generate_ai_plan(
        req, llm, model_manager=score_model_manager, config=config
    )

    duration = round(time.time() - start_time, 3)

    logger.info(f"[CHAT_API_SUCCESS] user_id={req.user_id} " f"duration={duration}s")

    return result
