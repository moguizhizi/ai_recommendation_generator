# app/controllers/chat_controller.py

import time
import logging
from fastapi import APIRouter, Request
from app.schemas.chat import AIRecPlanRequest, AIRecPlanResponse
from app.services.chat_service import generate_ai_plan
from llm.base import BaseLLM

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/chat", response_model=AIRecPlanResponse)
def chat_api(req: AIRecPlanRequest, request: Request):

    llm: BaseLLM = request.app.state.llm

    start_time = time.time()

    logger.info(
        f"[CHAT_API_START] user_id={req.user_id} " f"patient_code={req.patient_code} "
    )

    try:
        result = generate_ai_plan(req, llm)

        duration = round(time.time() - start_time, 3)

        logger.info(
            f"[CHAT_API_SUCCESS] user_id={req.user_id} " f"duration={duration}s"
        )

        return result

    except Exception as e:
        duration = round(time.time() - start_time, 3)

        logger.exception(
            f"[CHAT_API_ERROR] user_id={req.user_id} "
            f"duration={duration}s "
            f"error={str(e)}"
        )

        raise
