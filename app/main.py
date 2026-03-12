# app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

from configs.loader import load_config
from llm.factory import create_llm

from app.controllers.chat_controller import router as chat_router
from app.controllers.health_controller import router as health_router

from utils.logger import setup_logging, get_logger
from models.model_factory import ModelManager


# 初始化日志系统
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ========= 启动阶段 =========
    logger.info("Starting AI Recommendation Service...")

    try:
        config = load_config()
        logger.info("Configuration loaded successfully")

        app.state.llm = create_llm(config)
        logger.info("LLM instance created successfully")

        # ML models
        model_manager = ModelManager()
        model_manager.load_models(config)

        app.state.model_manager = model_manager

        logger.info("All models loaded successfully")

    except Exception as e:
        logger.exception("Failed to initialize LLM during startup")
        raise e

    yield

    # ========= 关闭阶段 =========
    logger.info("Shutting down AI Recommendation Service...")

    llm = getattr(app.state, "llm", None)

    if llm and hasattr(llm, "session"):
        try:
            llm.session.close()
            logger.info("LLM session closed successfully")
        except Exception:
            logger.exception("Error while closing LLM session")

    logger.info("Shutdown complete")


app = FastAPI(title="AI Recommendation Service", lifespan=lifespan)

app.include_router(chat_router, prefix="/api")
app.include_router(health_router, prefix="/api")
