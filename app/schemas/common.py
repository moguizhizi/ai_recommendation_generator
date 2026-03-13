from pydantic import BaseModel, Field, field_validator
from typing import Optional


class Task(BaseModel):

    task_id: str = Field(..., title="任务ID")
    task_name: str = Field(..., title="任务名称")

    paradigm: Optional[str] = Field(None, title="训练范式")
    cognitive_domain: Optional[str] = Field(None, title="一级脑能力")

    difficulty: Optional[float] = Field(None, title="难度等级")
    start_level: Optional[int] = Field(None, title="起始难度等级")
    level_max: Optional[int] = Field(None, title="级别上限")
    initial_difficulty: Optional[float] = Field(None, title="初始难度")

    life_interpretation: Optional[str] = Field(None, title="生活解读")

    min_duration: Optional[int] = Field(None, title="预计最小耗时")
    max_duration: Optional[int] = Field(None, title="预计最大耗时")

    training_time: Optional[int] = Field(None, title="训练时间")

    # 自动把 id 转为 str
    @field_validator("task_id", mode="before")
    @classmethod
    def normalize_id(cls, v):
        if v is None:
            raise ValueError("task_id 不能为空")
        return str(v)
