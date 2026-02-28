# app/services/plan_rule_engine.py
from app.core.constants import ModuleName, UserType, ScoreThreshold
from typing import Dict, List

ABILITY_NAME_MAP = {
    "memory": "记忆力",
    "exec": "执行控制",
    "attention": "注意力",
    "perception": "感知觉",
}

# 用户类型 -> 模块映射（集中管理）
USER_TYPE_MODULE_MAP = {
    UserType.ADVANTAGE: [
        ModuleName.ADVANTAGE_EXPAND,
        ModuleName.BALANCED_TRAIN,
    ],
    UserType.POTENTIAL: [
        ModuleName.POTENTIAL_EXPAND,
        ModuleName.BALANCED_TRAIN,
    ],
    UserType.SPECIAL: [
        ModuleName.CORE_STRENGTHEN,
        ModuleName.RELATED_ENHANCE,
    ],
    UserType.GROWTH: [
        ModuleName.BASIC_STABLE,
        ModuleName.STEP_UP,
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
    if any(
        ScoreThreshold.POTENTIAL_LINE <= v < ScoreThreshold.ADVANTAGE_LINE
        for v in level1_values
    ):
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


def build_advantage_user_modules(level1_scores: Dict[str, int]) -> Dict[str, List[str]]:
    """
    构建【优势倾向型】用户的训练模块结构

    规则：
    1. 一级脑能力 >= 100 的项作为候选
    2. 按分数降序排序
    3. 取最高的 2 项（不足 2 项则全取） → 优势能力拓展模块
    4. 剩余所有能力 → 能力均衡训练模块
    """

    # --- 1️⃣ 过滤 >= 100 的能力 ---
    qualified = [
        (ability, score) for ability, score in level1_scores.items() if score >= 100
    ]

    # --- 2️⃣ 按分数降序排序 ---
    qualified_sorted = sorted(qualified, key=lambda x: x[1], reverse=True)

    # --- 3️⃣ 取前 2 项（可能只有 0/1 项）---
    top_two = [ability for ability, _ in qualified_sorted[:2]]

    # --- 4️⃣ 剩余全部能力 ---
    balanced = [ability for ability in level1_scores.keys() if ability not in top_two]

    # --- 5️⃣ 构建训练名称 ---
    advantage_trainings = [f"{ABILITY_NAME_MAP.get(a, a)}进阶训练" for a in top_two]

    balanced_trainings = [f"{ABILITY_NAME_MAP.get(a, a)}巩固训练" for a in balanced]

    return {
        ModuleName.ADVANTAGE_EXPAND: advantage_trainings,
        ModuleName.BALANCED_TRAIN: balanced_trainings,
    }


# def build_recommended_modules(user_type: str, profile: dict):
#     for module in USER_TYPE_MODULE_MAP[user_type]:
#         module_name = module


#         class TrainingItem(BaseModel):
#         name: str = Field(..., title="训练项名称", description="如：感知觉进阶训练、注意力巩固训练")
#         tasks: List[str] = Field(..., title="具体训练任务列表", description="该训练项包含的具体游戏/任务名称")
#         difficulty: str = Field(..., title="训练难度", description="如：当前能力层级+0.5~1级")
#         frequency: str = Field(..., title="训练频次", description="如：每日1次，每次4-8分钟")
#         goal: str = Field(..., title="训练目标", description="该训练项期望达到的能力提升目标")
#         description: Optional[str] = Field(None, title="模块说明", description="可选说明，如：低压力、高成功体验")
