# app/schemas/common.py
from typing import List, Optional
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str = Field(..., title="任务ID")
    name: str = Field(..., title="任务名称")
    difficulty: Optional[float] = Field(None, title="难度等级")
    life_desc: Optional[str] = Field(None, title="生活场景描述")
    paradigm: Optional[str] = Field(None, title="训练范式")
    duration_min: Optional[int] = Field(None, title="建议训练时长（分钟）")

    level1_brain: Optional[str] = Field(None, title="一级脑能力")
    level2_brain: List[str] = Field(default_factory=list, title="二级脑能力列表")
