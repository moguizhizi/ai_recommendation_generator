# app/schemas/chat.py
from typing import List, Optional
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import BizError


class DimensionScorePrediction(BaseModel):
    historical_score: int = Field(
        ...,
        title="历史分数",
        description="用于预测的最近阶段历史分数（如最近一次或最近周期平均）",
    )

    predicted_score: int = Field(
        ...,
        title="预测分数",
        description="基于推荐任务干预后的预测分数",
    )

    baseline_predicted_score: int = Field(
        ...,
        title="无任务预测分数",
        description="在没有推荐任务干预情况下，基于历史趋势的自然预测分数",
    )


class ScorePrediction(BaseModel):
    summary: str = Field(
        ...,
        title="AI 分数预测说明",
        description="对下一阶段能力变化的预测说明文案",
    )

    attention: DimensionScorePrediction = Field(..., title="注意力完成度预测")
    memory: DimensionScorePrediction = Field(..., title="记忆力完成度预测")
    executive_control: DimensionScorePrediction = Field(..., title="执行控制完成度预测")
    perception: DimensionScorePrediction = Field(..., title="感知觉完成度预测")


class AIRecPlanRequest(BaseModel):
    user_id: Optional[str] = Field(
        None,
        title="用户ID",
        description="平台内唯一用户标识",
    )
    patient_code: Optional[str] = Field(
        None,
        title="患者编码",
        description="患者唯一业务编码",
    )

    @model_validator(mode="after")
    def check_at_least_one(cls, values):
        if not values.user_id and not values.patient_code:
            raise BizError(ErrorCode.MISSING_USER_IDENTIFIER)
        return values


class TrainingItem(BaseModel):
    name: str = Field(
        ..., title="训练项名称", description="如：感知觉进阶训练、注意力巩固训练"
    )
    tasks: str = Field(
        ..., title="具体训练任务列表", description="该训练项包含的具体游戏/任务名称"
    )
    difficulty: str = Field(
        ..., title="训练难度", description="如：当前能力层级+0.5~1级"
    )
    frequency: str = Field(
        ..., title="训练频次", description="如：每日1次，每次4-8分钟"
    )
    goal: str = Field(
        ..., title="训练目标", description="该训练项期望达到的能力提升目标"
    )
    description: Optional[str] = Field(
        None, title="模块说明", description="可选说明，如：低压力、高成功体验"
    )


class TrainingModule(BaseModel):
    module_name: str = Field(
        ..., title="模块名称", description="如：优势能力拓展模块 / 核心能力强化模块"
    )
    items: List[TrainingItem] = Field(..., title="模块内训练项列表")

class L2AbilityStat(BaseModel):
    name: str = Field(..., title="二级脑能力名称")
    count: int = Field(..., title="任务数量")
    ratio: float = Field(..., title="占比")


class AIRecPlanData(BaseModel):
    user_type: Literal["优势倾向型", "潜能倾向型", "专项优势型", "蓄力成长型"]

    overview: str = Field(
        ...,
        title="方案开篇概述",
        description="固定开篇文案，用于向家长说明本次AI方案的整体目标",
    )

    training_plan_intro: str = Field(
        ...,
        title="训练计划引导语",
        description="对训练模块的整体说明与导读",
    )

    modules: List[TrainingModule] = Field(
        ...,
        title="训练模块列表",
        description="不同用户类型对应不同模块组合",
    )

    score_prediction: ScorePrediction = Field(
        ...,
        title="AI 分数预测模块",
        description="包含预测说明文案与四个维度预测数据",
    )

    home_advice: List[str] = Field(
        ...,
        title="居家训练建议",
        description="固定文案，给家长的家庭训练建议",
    )

    tracking_and_adjustment: List[str] = Field(
        ...,
        title="效果追踪与动态调整说明",
        description="固定文案，描述数据监测与任务迭代规则",
    )

    raw_text: str = Field(
        ...,
        title="LLM 原始输出",
        description="模型原始生成全文，用于审计与调试",
    )

    l2_ability_distribution: List[L2AbilityStat] = Field(
        ...,
        title="二级脑能力分布",
        description="推荐任务中各二级脑能力的占比与数量"
    )


class AIRecPlanResponse(BaseModel):
    data: AIRecPlanData = Field(
        ...,
        title="结构化训练方案数据",
        description="AI生成的结构化训练方案内容",
    )

    display_text: str = Field(
        ...,
        title="方案展示全文",
        description="由结构化数据渲染生成的完整展示文本，用于前端直接展示或报告导出",
    )
