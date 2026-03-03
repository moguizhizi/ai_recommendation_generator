from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/health")
def health_check():
    logger.info("Health check called")
    return {"status": "ok"}


@router.get("/ready")
def readiness_check(request: Request):
    """
    检查服务是否 ready（比如 LLM 是否加载成功）
    """
    logger.info("Readiness check called")

    llm = getattr(request.app.state, "llm", None)

    if llm is None:
        logger.warning("Readiness check failed: LLM not initialized")
        return JSONResponse(status_code=503, content={"status": "not_ready"})

    logger.info("Readiness check passed: LLM is ready")
    return {"status": "ready"}
