# app/services/plan_rule_engine.py
from app.core.constants import ModuleName, UserType, ScoreThreshold
from typing import Dict, List, Tuple
from collections import defaultdict
from app.schemas.chat import TrainingItem, TrainingModule
from app.schemas.common import Task
from app.services.modules_processor import (
    fetch_tasks_by_ability,
    calc_difficulty,
    fetch_frequency,
    generate_goal_by_llm,
    get_missed_tasks_grouped_by_paradigm,
)
from llm.base import BaseLLM

from app.core.logging import get_logger

logger = get_logger(__name__)

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


def enrich_user_profile_with_tasks(profile: dict, task_repo: dict) -> dict:
    """
    基于原始 profile + 任务仓库 task_repo，对用户画像做一次「任务视图增强」
    """
    task_index: Dict[int, Task] = task_repo["task_index"]
    enriched_profile = dict(profile)  # 浅拷贝

    # --- 1️⃣ last_task -> last_task_info ---
    last_task_info = None
    last_task = profile.get("last_task")
    if last_task:
        task_id = last_task.get("id")
        task_obj = task_index.get(task_id)
        if task_obj:
            last_task_info = task_obj
            logger.debug(f"[ENRICH] last_task id={task_id} mapped to Task object")
        else:
            logger.debug(f"[ENRICH] last_task id={task_id} not found in task_index")
    else:
        logger.debug("[ENRICH] no last_task found in profile")

    # --- 2️⃣ weekly_missed_tasks -> weekly_missed_task_infos ---
    missed_task_infos: List[Task] = []
    missed_tasks = profile.get("weekly_missed_tasks", [])
    for missed in missed_tasks:
        task_id = missed.get("id")
        task_obj = task_index.get(task_id)
        if task_obj:
            missed_task_infos.append(task_obj)
            logger.debug(f"[ENRICH] missed_task id={task_id} mapped to Task object")
        else:
            logger.debug(f"[ENRICH] missed_task id={task_id} not found in task_index")

    logger.debug(
        f"[ENRICH] total missed tasks processed: {len(missed_task_infos)}/{len(missed_tasks)}"
    )

    # --- 3️⃣ 清理旧字段 ---
    enriched_profile.pop("last_task", None)
    enriched_profile.pop("weekly_missed_tasks", None)

    # --- 4️⃣ 写入增强后的字段 ---
    enriched_profile["last_task_info"] = last_task_info
    enriched_profile["weekly_missed_task_infos"] = missed_task_infos

    logger.debug(
        f"[ENRICH] profile enrichment complete for user_id={profile.get('user_id')}"
    )

    return enriched_profile


def enrich_profile_with_user_type(profile: dict) -> dict:
    """
    给用户画像 profile 打上 user_type 标签（写回 profile 并返回）
    """
    level1_scores = profile.get("level1_scores", {})
    level2_scores = profile.get("level2_scores", {})

    level1_values = [v for v in level1_scores.values() if isinstance(v, (int, float))]

    # 默认值
    user_type = UserType.GROWTH
    reason = "默认蓄力成长型"

    # 1️⃣ 优势倾向型
    if any(v >= ScoreThreshold.ADVANTAGE_LINE for v in level1_values):
        user_type = UserType.ADVANTAGE
        reason = "一级脑能力 ≥ ADVANTAGE_LINE"

    # 2️⃣ 潜能倾向型
    elif any(
        ScoreThreshold.POTENTIAL_LINE <= v < ScoreThreshold.ADVANTAGE_LINE
        for v in level1_values
    ):
        user_type = UserType.POTENTIAL
        reason = "一级脑能力 ∈ [POTENTIAL_LINE, ADVANTAGE_LINE)"

    # 3️⃣ 专项优势型（二级能力存在明显优势）
    else:
        for _, sub_scores in level2_scores.items():
            for v in sub_scores.values():
                if isinstance(v, (int, float)) and v > ScoreThreshold.ADVANTAGE_LINE:
                    user_type = UserType.SPECIAL
                    reason = "二级脑能力 > ADVANTAGE_LINE"
                    break

    enriched_profile = dict(profile)  # 浅拷贝，避免污染原对象
    enriched_profile["user_type"] = user_type

    # --- debug 日志 ---
    user_id = profile.get("user_id", "unknown")
    logger.debug(
        f"[ENRICH_PROFILE] user_id={user_id} "
        f"level1_scores={level1_scores} "
        f"level2_scores={level2_scores} "
        f"user_type={user_type} "
        f"reason={reason}"
    )

    return enriched_profile


def build_user_modules_by_threshold(
    enriched_profile: dict,
    level2_to_level1: Dict[str, str],
    threshold: int,
    llm: BaseLLM,
) -> List[TrainingModule]:
    level1_scores: Dict[str, int] = enriched_profile.get("level1_scores", {})
    level2_scores: Dict[str, Dict[str, int]] = enriched_profile.get("level2_scores", {})
    weekly_missed_task_infos: List[Task] = enriched_profile.get(
        "weekly_missed_task_infos", []
    )
    last_task: Task | None = enriched_profile.get("last_task_info")
    user_type: UserType = enriched_profile.get("user_type", UserType.GROWTH)
    user_id = enriched_profile.get("user_id", "unknown")

    level1_to_level2_map: Dict[str, List[str]] = defaultdict(list)
    remaining_level1_to_level2_map: Dict[str, List[str]] = defaultdict(list)

    # --- 计算 top_two / balanced ---
    top_two: List[str] = []
    balanced: List[str] = []

    if user_type in (UserType.SPECIAL, UserType.GROWTH):
        level2_list: List[Tuple[str, int]] = [
            (level2_key, score)
            for _, sub_scores in level2_scores.items()
            for level2_key, score in sub_scores.items()
        ]

        if user_type == UserType.SPECIAL:
            filtered_level2 = [(k, v) for k, v in level2_list if v > threshold]
        else:
            filtered_level2 = [(k, v) for k, v in level2_list if v <= threshold]

        filtered_level2_sorted = sorted(
            filtered_level2, key=lambda x: x[1], reverse=True
        )
        hit_level2_keys = set()
        seen_level1 = set()

        for level2_key, _ in filtered_level2_sorted:
            level1_key = level2_to_level1.get(level2_key)
            if not level1_key:
                continue
            hit_level2_keys.add(level2_key)
            level1_to_level2_map[level1_key].append(level2_key)

            if level1_key not in seen_level1:
                top_two.append(level1_key)
                seen_level1.add(level1_key)
            if len(top_two) >= 2:
                break

        balanced = [k for k in level1_scores.keys() if k not in top_two]

        for level2_key, score in level2_list:
            if level2_key in hit_level2_keys:
                continue
            level1_key = level2_to_level1.get(level2_key)
            if not level1_key:
                continue
            remaining_level1_to_level2_map[level1_key].append(level2_key)

    else:
        qualified = [
            (ability, score)
            for ability, score in level1_scores.items()
            if score >= threshold
        ]
        qualified_sorted = sorted(qualified, key=lambda x: x[1], reverse=True)
        top_two = [ability for ability, _ in qualified_sorted[:2]]
        balanced = [
            ability for ability in level1_scores.keys() if ability not in top_two
        ]

    logger.debug(
        f"[BUILD_MODULES] user_id={user_id} user_type={user_type} threshold={threshold} "
        f"top_two={top_two} balanced={balanced} "
        f"level1_to_level2_map={dict(level1_to_level2_map)} "
        f"remaining_level1_to_level2_map={dict(remaining_level1_to_level2_map)}"
    )

    def build_training_item(
        level1_key: str,
        score: int,
        suffix: str,
        level2_keys: List[str] | None = None,
    ) -> TrainingItem:
        ability_name_cn = ABILITY_NAME_MAP.get(level1_key, level1_key)
        paradigm_tasks = get_missed_tasks_grouped_by_paradigm(
            level1_key, weekly_missed_task_infos, level2_keys=level2_keys
        )

        # 关键判断
        if not paradigm_tasks:
            logger.debug(
                f"[BUILD_TRAINING_ITEM_SKIP] user_id={user_id} "
                f"level1_key={level1_key} no paradigm_tasks"
            )
            return None

        item = TrainingItem(
            name=f"{ability_name_cn}{suffix}",
            tasks=fetch_tasks_by_ability(paradigm_tasks),
            difficulty=calc_difficulty(last_task, paradigm_tasks),
            frequency=fetch_frequency(paradigm_tasks),
            goal=generate_goal_by_llm(paradigm_tasks, llm),
            description="低压力、高成功体验",
        )
        logger.debug(
            f"[BUILD_TRAINING_ITEM] user_id={user_id} level1_key={level1_key} "
            f"level2_keys={level2_keys} name={item.name} tasks_count={len(item.tasks)} "
            f"difficulty={item.difficulty} frequency={item.frequency}"
        )
        return item

    advantage_items = [
        item
        for a in top_two
        if (
            item := build_training_item(
                level1_key=a,
                score=level1_scores.get(a, 0),
                suffix="进阶训练",
                level2_keys=level1_to_level2_map.get(a),
            )
        )
    ]

    balanced_items = [
        item
        for a in balanced
        if (
            item := build_training_item(
                level1_key=a,
                score=level1_scores.get(a, 0),
                suffix="巩固训练",
                level2_keys=level1_to_level2_map.get(a),
            )
        )
    ]

    module_names = USER_TYPE_MODULE_MAP.get(
        user_type, USER_TYPE_MODULE_MAP[UserType.GROWTH]
    )
    module_items_map = {
        ModuleName.ADVANTAGE_EXPAND: advantage_items,
        ModuleName.POTENTIAL_EXPAND: advantage_items,
        ModuleName.CORE_STRENGTHEN: advantage_items,
        ModuleName.BASIC_STABLE: advantage_items,
        ModuleName.BALANCED_TRAIN: balanced_items,
        ModuleName.RELATED_ENHANCE: balanced_items,
        ModuleName.STEP_UP: balanced_items,
    }

    modules = [
        TrainingModule(
            module_name=module_name, items=module_items_map.get(module_name, [])
        )
        for module_name in module_names
    ]

    logger.debug(f"[BUILD_MODULES_DONE] user_id={user_id} modules_count={len(modules)}")
    return modules


def build_advantage_user_modules(
    enriched_profile: dict, level2_to_level1: dict, llm: BaseLLM
) -> List[TrainingModule]:
    """
    构建【优势倾向型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.ADVANTAGE_LINE,
        llm=llm,
    )


def build_potential_user_modules(
    enriched_profile: dict, level2_to_level1: dict, llm: BaseLLM
) -> List[TrainingModule]:
    """
    构建【潜能倾向型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.POTENTIAL_LINE,
        llm=llm,
    )


def build_special_user_modules(
    enriched_profile: dict, level2_to_level1: dict, llm: BaseLLM
) -> List[TrainingModule]:
    """
    构建【专项优势型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.ADVANTAGE_LINE,
        llm=llm,
    )


def build_growth_user_modules(
    enriched_profile: dict, level2_to_level1: dict, llm: BaseLLM
) -> List[TrainingModule]:
    """
    构建【蓄力成长型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.POTENTIAL_LINE,
        llm=llm,
    )


def get_fixed_templates(profile: dict) -> dict:
    templates = {
        UserType.ADVANTAGE.value: {
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
            "score_prediction": [
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。",
            ],
        },
        UserType.POTENTIAL.value: {
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
            "score_prediction": [
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。",
            ],
        },
        UserType.SPECIAL.value: {
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
            "score_prediction": [
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。",
            ],
        },
        UserType.GROWTH.value: {
            "overview": (
                "为了帮助孩子扭转能力波动下降的趋势，我们结合本阶段训练数据与能力现状，为孩子生成了专属的 AI 训练方案。"
                "方案以稳定能力、巩固基础、逐步提升为核心，帮助孩子重拾训练信心，稳步提升认知能力。"
                "建议您仔细阅读，和我们一起陪伴孩子走出波动期，建立更扎实的认知基础。"
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
            "score_prediction": [
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。",
            ],
        },
    }

    return templates.get(profile["user_type"], templates[UserType.GROWTH.value])
