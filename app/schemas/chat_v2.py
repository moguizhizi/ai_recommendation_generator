from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.chat import AIRecPlanData


class ResponseMetaV2(BaseModel):
    version: str = Field(..., title="接口版本")
    user_id: Optional[str] = Field(
        None,
        title="用户ID",
        description="请求中传入的用户ID",
    )
    patient_code: Optional[str] = Field(
        None,
        title="患者编码",
        description="请求中传入的患者编码",
    )


class AIRecPlanResponseV2(BaseModel):
    meta: ResponseMetaV2 = Field(
        ...,
        title="元信息",
        description="响应版本与请求标识信息",
    )
    plan: AIRecPlanData = Field(
        ...,
        title="结构化训练方案数据",
        description="AI生成的结构化训练方案内容",
    )
    display_text: str = Field(
        ...,
        title="方案展示全文",
        description="由结构化数据渲染生成的完整展示文本，用于前端直接展示或报告导出",
    )
