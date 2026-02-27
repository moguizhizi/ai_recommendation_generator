# app/schemas/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional
from typing import Literal

class AIRecPlanRequest(BaseModel):
    user_id: str = Field(..., title="用户ID", description="平台内唯一用户标识", example="1845646199363297282")
    patient_code: str = Field(..., title="患者编码", description="患者唯一业务编码", example="ETYY241028700")

class TrainingItem(BaseModel):
    name: str = Field(..., title="训练项名称", description="如：感知觉进阶训练、注意力巩固训练")
    tasks: List[str] = Field(..., title="具体训练任务列表", description="该训练项包含的具体游戏/任务名称")
    difficulty: str = Field(..., title="训练难度", description="如：当前能力层级+0.5~1级")
    frequency: str = Field(..., title="训练频次", description="如：每日1次，每次4-8分钟")
    goal: str = Field(..., title="训练目标", description="该训练项期望达到的能力提升目标")
    description: Optional[str] = Field(None, title="模块说明", description="可选说明，如：低压力、高成功体验")

class TrainingModule(BaseModel):
    module_name: str = Field(..., title="模块名称", description="如：优势能力拓展模块 / 核心能力强化模块")
    items: List[TrainingItem] = Field(..., title="模块内训练项列表")

class AIRecPlanResponse(BaseModel):
    user_type: Literal["优势倾向型", "潜能倾向型", "专项优势型", "蓄力成长型"]
    overview: str = Field(..., title="方案开篇概述", description="固定开篇文案，用于向家长说明本次AI方案的整体目标")
    training_plan_intro: str = Field(..., title="训练计划引导语", description="对训练模块的整体说明与导读")
    modules: List[TrainingModule] = Field(..., title="训练模块列表", description="不同用户类型对应不同模块组合")
    score_prediction: str = Field(..., title="AI 分数预测说明", description="对下一阶段能力变化的预测说明文案")
    home_advice: List[str] = Field(..., title="居家训练建议", description="固定文案，给家长的家庭训练建议")
    tracking_and_adjustment: List[str] = Field(..., title="效果追踪与动态调整说明", description="固定文案，描述数据监测与任务迭代规则")
    raw_text: str = Field(..., title="LLM 原始输出", description="模型原始生成全文，用于审计与调试")