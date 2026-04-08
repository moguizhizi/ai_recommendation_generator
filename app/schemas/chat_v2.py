from typing import List,  Optional

from pydantic import BaseModel, Field

from app.schemas.chat import (
    L2AbilityDistributionBlock,
    ScorePredictionBlock,
)


class TrainingPlanSection(BaseModel):
    title: str = Field(
        default="下阶段训练方案",
        description="训练方案主模块标题",
    )
    score_prediction: ScorePredictionBlock = Field(
        ...,
        title="分数预测",
        description="一级脑能力预测信息",
    )
    l2_block: L2AbilityDistributionBlock = Field(
        ...,
        title="能力占比",
        description="二级脑能力训练占比信息",
    )


class HomeAdviceSection(BaseModel):
    title: str = Field(
        default="居家训练建议",
        description="居家训练建议模块标题",
    )
    content: str = Field(
        ...,
        title="建议内容",
        description="给家长的居家训练建议文案",
    )


class TrainingTipsSection(BaseModel):
    title: str = Field(
        default="训练小贴士",
        description="训练小贴士模块标题",
    )
    items: List[str] = Field(
        ...,
        title="贴士列表",
        description="训练追踪与动态调整相关提示",
    )


class ResponseMetaV2(BaseModel):
    version: str = Field(..., title="接口版本")
    user_id: Optional[str] = Field(
        None,
        title="用户ID",
        description="用户ID",
    )
    patient_code: Optional[str] = Field(
        None,
        title="患者编码",
        description="患者编码",
    )


class AIRecPlanV2(BaseModel):

    training_plan_section: TrainingPlanSection = Field(
        ...,
        title="训练方案主模块",
        description="聚合分数预测和能力占比信息",
    )
    home_advice_section: HomeAdviceSection = Field(
        ...,
        title="居家训练建议",
        description="居家训练建议模块",
    )
    training_tips_section: TrainingTipsSection = Field(
        ...,
        title="训练小贴士",
        description="训练效果追踪与动态调整说明",
    )


class AIRecPlanResponseV2(BaseModel):
    meta: ResponseMetaV2 = Field(
        ...,
        title="元信息",
        description="响应版本与请求标识信息",
    )
    plan: AIRecPlanV2 = Field(
        ...,
        title="结构化训练方案数据",
        description="AI生成的结构化训练方案内容",
    )
