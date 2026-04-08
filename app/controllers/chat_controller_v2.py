import time
from typing import Any, Dict

from fastapi import APIRouter, Request

from app.schemas.chat import AIRecPlanRequest
from app.schemas.chat_v2 import AIRecPlanResponseV2
from app.services.chat_service import generate_ai_plan_v2
from llm.base import BaseLLM
from models.model_factory import ModelManager
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v2", tags=["chat-v2"])


@router.post("/chat", response_model=AIRecPlanResponseV2)
def chat_api_v2(req: AIRecPlanRequest, request: Request):
    llm: BaseLLM = request.app.state.llm
    score_model_manager: ModelManager = request.app.state.model_manager
    config: Dict[str, Any] = request.app.state.config

    start_time = time.time()

    logger.info(
        f"[CHAT_API_V2_START] user_id={req.user_id} patient_code={req.patient_code}"
    )

    result = generate_ai_plan_v2(
        req, llm, model_manager=score_model_manager, config=config
    )

    duration = round(time.time() - start_time, 3)

    logger.info(f"[CHAT_API_V2_SUCCESS] user_id={req.user_id} duration={duration}s")

    return result
