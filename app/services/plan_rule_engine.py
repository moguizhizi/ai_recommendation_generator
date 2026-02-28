# app/services/plan_rule_engine.py
from app.core.constants import UserType, ScoreThreshold

USER_TYPE_MODULE_MAP = {
    "优势倾向型": [
        "优势能力拓展模块",
        "能力均衡训练模块",
    ],
    "潜能倾向型": [
        "认知潜能拓展模块",
        "能力均衡训练模块",
    ],
    "专项优势型": [
        "核心能力强化模块",
        "关联能力提升训练模块",
    ],
    "蓄力成长型": [
        "基础能力稳控模块",
        "阶梯式提升模块",
    ],
}


def calc_user_type(profile: dict) -> str:
    """
    判定顺序：
    1. 优势倾向型：任意一级脑能力 ≥ 100
    2. 潜能倾向型：任意一级脑能力 ∈ [90, 100)
    3. 专项优势型：任意二级脑能力 > 100
    4. 蓄力成长型：所有一级脑能力 < 90
    """

    level1_scores = profile.get("level1_scores", {})
    level2_scores = profile.get("level2_scores", {})

    level1_values = [v for v in level1_scores.values() if v > 0]

    # 1️⃣ 优势倾向型
    if any(v >= ScoreThreshold.ADVANTAGE_LINE for v in level1_values):
        return UserType.ADVANTAGE.value

    # 2️⃣ 潜能倾向型
    if any(ScoreThreshold.POTENTIAL_LINE <= v < ScoreThreshold.ADVANTAGE_LINE for v in level1_values):
        return UserType.POTENTIAL.value

    # 3️⃣ 专项优势型（二级能力存在明显优势）
    for _, sub_scores in level2_scores.items():
        for v in sub_scores.values():
            if v > ScoreThreshold.ADVANTAGE_LINE:
                return UserType.SPECIAL.value

    # 4️⃣ 蓄力成长型
    if level1_values and all(v < ScoreThreshold.POTENTIAL_LINE for v in level1_values):
        return UserType.GROWTH.value

    return UserType.GROWTH.value


# app/services/plan_rule_engine.py
from typing import Dict, List


ABILITY_NAME_MAP = {
    "memory": "记忆力",
    "exec": "执行控制",
    "attention": "注意力",
    "perception": "感知觉",
}


def build_advantage_user_modules(level1_scores: Dict[str, int]) -> Dict[str, List[str]]:
    """
    构建【优势倾向型】用户的训练模块结构

    规则：
    1. 一级脑能力 >= 100 的项作为候选
    2. 按分数降序排序
    3. 取最高的 2 项 → 优势能力拓展模块
    4. 其余项 → 能力均衡训练模块
    """

    # --- 1️⃣ 过滤 >=100 的能力 ---
    qualified = {
        ability: score
        for ability, score in level1_scores.items()
        if score >= 100
    }

    # --- 2️⃣ 按分数降序排序 ---
    sorted_items = sorted(qualified.items(), key=lambda x: x[1], reverse=True)

    # --- 3️⃣ 取前 2 项 ---
    top_two = [ability for ability, _ in sorted_items[:2]]

    # --- 4️⃣ 其余能力（用于能力均衡模块）---
    balanced = [ability for ability in level1_scores.keys() if ability not in top_two]

    # --- 5️⃣ 构建训练名称 ---
    advantage_trainings = [
        f"{ABILITY_NAME_MAP[a]}进阶训练" for a in top_two
    ]

    balanced_trainings = [
        f"{ABILITY_NAME_MAP[a]}巩固训练" for a in balanced
    ]

    return {
        "优势能力拓展模块": advantage_trainings,
        "能力均衡训练模块": balanced_trainings
    }




def build_recommended_modules(user_type: str, profile: dict):
    for module in USER_TYPE_MODULE_MAP[user_type]:
        module_name = module


        

        class TrainingItem(BaseModel):
        name: str = Field(..., title="训练项名称", description="如：感知觉进阶训练、注意力巩固训练")
        tasks: List[str] = Field(..., title="具体训练任务列表", description="该训练项包含的具体游戏/任务名称")
        difficulty: str = Field(..., title="训练难度", description="如：当前能力层级+0.5~1级")
        frequency: str = Field(..., title="训练频次", description="如：每日1次，每次4-8分钟")
        goal: str = Field(..., title="训练目标", description="该训练项期望达到的能力提升目标")
        description: Optional[str] = Field(None, title="模块说明", description="可选说明，如：低压力、高成功体验")