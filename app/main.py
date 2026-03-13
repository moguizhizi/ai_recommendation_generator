# app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.tasks.sync_manager import start_sync_tasks
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

    logger.info("Starting AI Recommendation Service...")

    try:
        config = load_config()

        app.state.config = config

        app.state.llm = create_llm(config)

        model_manager = ModelManager()
        model_manager.load_models(config)

        app.state.model_manager = model_manager

        start_sync_tasks(config)

    except Exception as e:
        logger.exception("Failed to initialize services")
        raise e

    yield

    logger.info("Shutting down AI Recommendation Service...")


app = FastAPI(title="AI Recommendation Service", lifespan=lifespan)

app.include_router(chat_router, prefix="/api")
app.include_router(health_router, prefix="/api")
