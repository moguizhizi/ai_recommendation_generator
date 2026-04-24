# app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.errors.error_handler import biz_error_handler, generic_error_handler
from app.core.errors.exceptions import BizError
from app.tasks.sync_manager import start_sync_tasks
from configs.loader import load_config
from llm.factory import create_llm

from app.controllers.chat_controller import router as chat_router
from app.controllers.chat_controller_v2 import router as chat_router_v2
from app.controllers.health_controller import router as health_router
from app.controllers.evaluation_controller import router as eval_router

from utils.logger import setup_logging, get_logger
from models.model_factory import ModelManager


# 初始化日志系统
setup_logging()
logger = get_logger(__name__)
bootstrap_config = load_config()


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting AI Recommendation Service...")

    try:
        config = bootstrap_config

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

app.add_exception_handler(BizError, biz_error_handler)

app.add_exception_handler(Exception, generic_error_handler)

# Router enable/disable is controlled by configs/config.yaml.
if bootstrap_config.get("routers", {}).get("chat_router_enabled", True):
    app.include_router(chat_router, prefix="/api")

app.include_router(chat_router_v2, prefix="/api")
app.include_router(health_router, prefix="/api")

if bootstrap_config.get("routers", {}).get("eval_router_enabled", True):
    app.include_router(eval_router, prefix="/api")
