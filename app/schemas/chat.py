# app/schemas/chat.py
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="用户ID")
    patient_code: str = Field(..., description="患者编码")

class ChatResponse(BaseModel):
    result: str