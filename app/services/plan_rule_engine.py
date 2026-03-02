# app/services/plan_rule_engine.py
from app.core.constants import ModuleName, UserType, ScoreThreshold
from typing import Dict, List
from app.schemas.chat import TrainingItem, TrainingModule
from app.services.modules_processor import (
    fetch_tasks_by_ability,
    calc_difficulty,
    fetch_frequency,
    generate_goal_by_llm,
    get_missed_tasks_grouped_by_paradigm,
)

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



def build_user_modules_by_threshold(
    level1_scores: Dict[str, int],
    threshold: int,
) -> List[TrainingModule]:
    """
    通用构建用户训练模块结构
    - threshold: 分数阈值（潜能 / 优势）
    """

    # --- 1️⃣ 过滤 >= threshold 的能力 ---
    qualified = [
        (ability, score)
        for ability, score in level1_scores.items()
        if score >= threshold
    ]

    # --- 2️⃣ 按分数降序排序 ---
    qualified_sorted = sorted(qualified, key=lambda x: x[1], reverse=True)

    # --- 3️⃣ 取前 2 项 ---
    top_two = [ability for ability, _ in qualified_sorted[:2]]

    # --- 4️⃣ 剩余全部能力 ---
    balanced = [ability for ability in level1_scores.keys() if ability not in top_two]

    # --- 5️⃣ 组装 TrainingItem ---
    def build_training_item(ability_key: str, score: int, suffix: str) -> TrainingItem:
        ability_name_cn = ABILITY_NAME_MAP.get(ability_key, ability_key)
        paradigm_tasks = get_missed_tasks_grouped_by_paradigm(ability_key, task_info)

        return TrainingItem(
            name=f"{ability_name_cn}{suffix}",
            tasks=fetch_tasks_by_ability(paradigm_tasks),
            difficulty=calc_difficulty(ability_key, score),
            frequency=fetch_frequency(paradigm_tasks),
            goal=generate_goal_by_llm(ability_name_cn),
            description="低压力、高成功体验",
        )

    advantage_items = [
        build_training_item(a, level1_scores[a], "进阶训练") for a in top_two
    ]

    balanced_items = [
        build_training_item(a, level1_scores[a], "巩固训练") for a in balanced
    ]

    # --- 6️⃣ 返回模块结构 ---
    return [
        TrainingModule(module_name=ModuleName.ADVANTAGE_EXPAND, items=advantage_items),
        TrainingModule(module_name=ModuleName.BALANCED_TRAIN, items=balanced_items),
    ]

def build_potential_user_modules(level1_scores: Dict[str, int]) -> List[TrainingModule]:
    """
    构建【潜能倾向型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        level1_scores=level1_scores,
        threshold=ScoreThreshold.POTENTIAL_LINE,
    )


def build_advantage_user_modules(level1_scores: Dict[str, int]) -> List[TrainingModule]:
    """
    构建【优势倾向型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        level1_scores=level1_scores,
        threshold=ScoreThreshold.ADVANTAGE_LINE,
    )


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


def get_fixed_templates(user_type: str) -> dict:
    templates = {
        "优势倾向型": {
            "overview": (
                "为了让训练更高效、更贴合孩子的成长节奏，我们结合本阶段的认知训练数据与优势倾向，"
                "为孩子生成了专属的 AI 训练方案。这份方案精准匹配宝贝的能力发展节奏，能更有针对性地助力孩子提升认知能力。"
                "建议您仔细阅读，和我们一起助力孩子认知成长。"
            ),
            "training_plan_intro": (
                "训练任务将围绕孩子优势倾向展开，以下是 AI 生成的一周专属训练计划，"
                "通过强化优势、带动均衡，精准匹配孩子当前的能力水平与发展需求。"
            ),
            "home_advice": [
                "生活功能场景：听新闻后复述4-5个信息点，锻炼孩子记忆联结能力。",
                "家庭延伸训练：每日可增加10分钟“家庭寻宝游戏”（锻炼感知觉）或“时间管理小任务”（锻炼执行控制），强化能力迁移。",
                "正向反馈技巧：当孩子完成跨场景任务时，具体表扬其能力表现（如“你刚才在整理玩具时，按颜色和形状分类，执行控制能力用得真好！”），强化优势能力的应用意识。",
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线，对比感知觉、执行控制、注意力、记忆力的稳定性与训练效果；每3个月生成阶段报告，评估阶段训练效果及孩子生活行为改善情况。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。",
            ],
        },
        "潜能倾向型": {
            "overview": (
                "为保障认知训练的高效性与适配性，贴合孩子的个性化成长节奏，我们依托本阶段训练数据，"
                "结合孩子的认知潜能倾向，为其定制专属 AI 训练方案。方案精准匹配宝贝的认知发展节奏，"
                "可针对性助力认知能力提升，建议您详细阅读。"
            ),
            "training_plan_intro": (
                "为了让训练效果最大化，我们将训练计划拆解为两大模块：认知潜能拓展聚焦强化孩子的潜能，"
                "能力均衡训练则巩固基础、补齐短板。以下为 AI 推荐的一周训练安排。"
            ),
            "home_advice": [
                "生活功能场景：玩“听记数字”游戏（家长报数字串，孩子复述，逐步增加长度），锻炼孩子信息加工速度。",
                "家庭延伸训练：玩“干扰游戏”（家长制造轻微噪音，孩子专注拼图）。",
                "正向反馈技巧：和孩子一起讨论“分心时如何拉回注意力”（如捏耳垂、默念“专注”），陪孩子一起想办法做到。",
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线；每3个月生成阶段报告。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。",
            ],
        },
        "专项优势型": {
            "overview": (
                "本方案结合孩子本阶段训练数据与专项优势特征制定。通过优势能力深化、巩固基础能力，"
                "将实验室得分转化为临床功能改善，最终提升孩子的生活能力表现。建议您详细阅读。"
            ),
            "training_plan_intro": (
                "基于孩子的专项优势能力，我们以核心能力强化 + 关联能力联动提升为原则，"
                "为孩子制定了周度训练任务方案。"
            ),
            "home_advice": [
                "生活功能场景：分心时在本子上记录“刚才想了什么”，事后一起分析干扰源。",
                "家庭环境打造：为孩子创建低干扰学习环境，减少视觉与听觉分心源，背景噪音控制在 40-50 分贝。",
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线；每3个月生成阶段报告。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。",
            ],
        },
        "蓄力成长型": {
            "overview": (
                "为了帮助孩子扭转能力波动下降的趋势，我们结合本阶段训练数据与能力现状，为孩子生成了专属的 AI 训练方案。"
                "方案以稳定能力、巩固基础、逐步提升为核心，帮助孩子重拾训练信心，稳步提升认知能力。"
                "建议您仔细阅读，陪伴孩子走出波动期。"
            ),
            "training_plan_intro": (
                "本阶段训练以“低压力、高成功体验”为原则，通过基础稳控 + 阶梯式提升，逐步改善能力表现。"
            ),
            "home_advice": [
                "生活功能场景：听新闻后复述4-5个信息点，锻炼孩子记忆联结能力。",
                "家庭延伸训练：每日增加10分钟“家庭寻宝游戏”或“时间管理小任务”，强化能力迁移。",
                "正向反馈技巧：具体表扬孩子的努力过程，而不仅是结果，增强信心。",
            ],
            "tracking_and_adjustment": [
                "数据监测：系统会每日记录任务完成率并推送日报；每周生成能力变化曲线；每3个月生成阶段报告。",
                "迭代规则：每天更新任务，同一个训练任务连续出现不超过3天。",
            ],
        },
    }

    return templates.get(user_type, templates["潜能倾向型"])
