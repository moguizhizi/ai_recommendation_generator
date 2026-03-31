from app.core.cognitive_l1.constants import L1_INDEX, L2_INDEX
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Tuple


from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List, Tuple


class Task(BaseModel):

    task_id: str = Field(..., title="任务ID")
    task_name: str = Field(..., title="任务名称")

    paradigm: Optional[str] = Field(None, title="训练范式")
    cognitive_domain: Optional[str] = Field(None, title="一级脑能力")
    sub_cognitive_domain: Optional[str] = Field(None, title="二级脑能力")

    difficulty: Optional[float] = Field(None, title="难度等级")
    start_level: Optional[int] = Field(None, title="起始难度等级")
    level_max: Optional[int] = Field(None, title="级别上限")
    initial_difficulty: Optional[float] = Field(None, title="初始难度")

    life_interpretation: Optional[str] = Field(None, title="生活解读")

    min_duration: Optional[int] = Field(None, title="预计最小耗时")
    max_duration: Optional[int] = Field(None, title="预计最大耗时")

    training_time: Optional[int] = Field(None, title="训练时间")

    # ✅ 坐标
    brain_coord: Optional[List[Tuple[int, int]]] = Field(
        default=None,
        title="脑能力坐标 (L1, L2)"
    )

    # ✅ 一级脑能力索引
    l1_index: Optional[int] = Field(
        default=None,
        title="一级脑能力索引"
    )

    # ✅ 二级脑能力索引
    l2_index: Optional[int] = Field(
        default=None,
        title="二级脑能力索引"
    )

    @field_validator("task_id", mode="before")
    @classmethod
    def normalize_id(cls, v):
        if v is None:
            raise ValueError("task_id 不能为空")
        return str(v)

    @model_validator(mode="after")
    def build_brain_coord(self):
        raw = self.sub_cognitive_domain

        if not raw:
            self.brain_coord = []
            self.l1_index = None
            self.l2_index = None
            return self

        # ✅ 只取第一个
        first_item = raw.split(";")[0]

        if "_" not in first_item:
            self.brain_coord = []
            self.l1_index = None
            self.l2_index = None
            return self

        l1_cn, l2_cn = first_item.split("_", 1)

        if l1_cn not in L1_INDEX or l2_cn not in L2_INDEX:
            self.brain_coord = []
            self.l1_index = None
            self.l2_index = None
            return self

        l1_idx = L1_INDEX[l1_cn]
        l2_idx = L2_INDEX[l2_cn]

        # ✅ 写入
        self.brain_coord = [(l1_idx, l2_idx)]
        self.l1_index = l1_idx
        self.l2_index = l2_idx

        return self
