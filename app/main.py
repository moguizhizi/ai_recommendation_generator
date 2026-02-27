# app/main.py
from fastapi import FastAPI
from app.controllers.chat_controller import router as chat_router
from app.controllers.health_controller import router as health_router

app = FastAPI(title="LLM Service")

app.include_router(chat_router, prefix="/api")
app.include_router(health_router, prefix="/api")

# uvicorn app.main:app --reload