# app/services/plan_rule_engine.py
import json
import random
from collections import defaultdict
from numbers import Number
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from app.core.cognitive_l1.constants import (
    L1_INDEX,
    L1_INDEX_REVERSE,
    L2_INDEX_REVERSE,
    Level2BrainDomain,
)
from app.core.constants import (
    LEVEL1_DOMAIN_KEY_MAP,
    Level1BrainDomain,
    ModuleName,
    Level1Score,
    ScoreThreshold,
    UserType,
)
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import BizError
from app.schemas.chat import (
    AIRecPlanData,
    DimensionScorePrediction,
    L2AbilityStat,
    ScorePrediction,
    TrainingItem,
    TrainingModule,
)
from app.schemas.common import Task
from app.services.modules_processor import (
    fetch_tasks_by_ability,
    calc_difficulty,
    fetch_frequency,
    generate_goal_by_llm,
    get_recommended_tasks_grouped_by_paradigm,
)
from llm.base import BaseLLM

from models.model_factory import ModelManager
from utils.logger import get_logger

logger = get_logger(__name__)

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

def enrich_user_profile_with_domain_histories(
    profile: dict, config: Dict[str, Any]
) -> dict:
    """
    为用户画像补充各脑能力的连续历史序列
    """
    min_history_len = int(config.get("score_prediction", {}).get("min_history_len", 3))

    def is_valid(value):
        return isinstance(value, Number)

    histories = {}

    for domain in Level1BrainDomain:
        domain_value = domain.value
        seq = []

        # latest
        latest_val = profile["latest_level1_scores"].get(domain_value)

        if not is_valid(latest_val):
            histories[domain_value] = []
            continue

        seq.append(latest_val)

        # week1 ~ week11
        for week in range(1, 12):
            week_scores = profile.get(f"week{week}_level1_scores")
            if not week_scores:
                break

            val = week_scores.get(domain_value)

            if not is_valid(val):
                break

            seq.append(val)

        seq = seq[::-1]  # 倒序，保证时间顺序从远到近
        histories[domain_value] = seq

    insufficient_histories = {
        domain: len(seq)
        for domain, seq in histories.items()
        if len(seq) < min_history_len + 1
    }

    if insufficient_histories:
        raise BizError(
            ErrorCode.NEW_USER_PLAN_NOT_AVAILABLE,
            user_id=profile.get("user_id", ""),
            patient_code=profile.get("patient_code", ""),
            min_history_len=min_history_len,
            insufficient_histories=insufficient_histories,
        )

    # 👇 挂到 profile 上
    profile["domain_histories"] = histories

    return profile


def enrich_user_profile_with_tasks(profile: dict, task_repo: dict) -> dict:
    """
    基于原始 profile + 任务仓库 task_repo，对用户画像做一次「任务视图增强」
    """
    task_index: Dict[int, Task] = task_repo["task_index"]
    enriched_profile = dict(profile)  # 浅拷贝

    # --- 1️⃣ last_task -> last_task_info ---
    last_day_task_info = None
    last_day_task = profile.get("last_day_task")

    if len(last_day_task) > 0:

        # 随机选一个任务
        task_str = random.choice(last_day_task)

        # 解析 task_id
        task_id = task_str.split("_", 1)[0]

        task_obj = task_index.get(task_id)

        if task_obj:
            last_day_task_info = task_obj
            logger.debug(f"[ENRICH] last_task id={task_id} mapped to Task object")
        else:
            raise BizError(
                ErrorCode.TASK_NOT_FOUND_IN_REPO,
                user_id=profile.get("user_id", ""),
                patient_code=profile.get("patient_code", ""),
                task_id=task_id,
            )

    else:
        raise BizError(
            ErrorCode.MISSING_LAST_TASK,
            user_id=profile.get("user_id", ""),
            patient_code=profile.get("patient_code", ""),
        )

    # --- 2️⃣ weekly_missed_tasks -> weekly_missed_task_infos ---
    missed_task_infos: List[Task] = []
    missed_tasks = profile.get("weekly_missed_tasks")

    if not isinstance(missed_tasks, list) or not missed_tasks:
        raise BizError(
            ErrorCode.MISSING_WEEKLY_MISSED_TASKS,
            user_id=profile.get("user_id", ""),
            patient_code=profile.get("patient_code", ""),
        )

    for task_str in missed_tasks:

        if isinstance(task_str, str) and "_" in task_str:

            task_id = task_str.split("_", 1)[0]
            task_obj = task_index.get(task_id)

            if task_obj:
                missed_task_infos.append(task_obj)
                logger.debug(f"[ENRICH] missed_task id={task_id} mapped to Task object")
            else:
                logger.warning(
                    f"[ENRICH] missed_task id={task_id} not found in task_index"
                )

        else:
            logger.warning(f"[ENRICH] invalid missed_task format: {task_str}")

    if not missed_task_infos:
        # 合并异常处理
        raise BizError(
            ErrorCode.MISSING_WEEKLY_MISSED_TASKS,
            user_id=profile.get("user_id", ""),
            patient_code=profile.get("patient_code", ""),
        )

    logger.debug(
        f"[ENRICH] total missed tasks processed: "
        f"{len(missed_task_infos)}/{len(missed_tasks) if len(missed_tasks) else 0}"
    )

    # --- 3️⃣ 清理旧字段 ---
    enriched_profile.pop("last_day_task", None)
    enriched_profile.pop("weekly_missed_tasks", None)

    # --- 4️⃣ 写入增强后的字段 ---
    enriched_profile["last_day_task_info"] = last_day_task_info
    enriched_profile["weekly_missed_task_infos"] = missed_task_infos

    logger.debug(
        f"[ENRICH] profile enrichment complete for user_id={profile.get('user_id')}"
    )

    return enriched_profile

def enrich_user_profile_with_brain_distribution(
    profile: Dict[str, Any],
    task_repo: Dict[str, Any],
    build_matrix: bool = False,  # 是否额外构建矩阵
) -> Dict[str, Any]:
    """
    基于 last_84_days_task 构建用户脑能力分布（L1 * L2）

    Args:
        profile: 用户画像
        task_repo: 任务仓库（包含 task_index）
        build_matrix: 是否构建 4x19 矩阵（默认 False）

    Returns:
        enriched_profile
    """

    task_index: Dict[str, Any] = task_repo.get("task_index", {})
    enriched_profile = dict(profile)  # 浅拷贝

    last_84_days_task = profile.get("last_84_days_task")

    # --- 1️⃣ 参数校验 ---
    if not isinstance(last_84_days_task, list) or not last_84_days_task:
        raise BizError(
            ErrorCode.NEW_USER_PLAN_NOT_AVAILABLE,
            user_id=profile.get("user_id", ""),
            patient_code=profile.get("patient_code", ""),
        )

    if not task_index:
        raise BizError(
            ErrorCode.TASK_REPO_EMPTY,
            user_id=profile.get("user_id", ""),
            patient_code=profile.get("patient_code", ""),
        )

    # --- 2️⃣ 统计 (l1, l2) ---
    counter: Dict[Tuple[int, int], int] = defaultdict(int)
    total = 0
    valid_task_cnt = 0

    for item in last_84_days_task:

        if not isinstance(item, str) or "_" not in item:
            logger.warning(f"[BRAIN_DIST] invalid task format: {item}")
            continue

        task_id = item.split("_", 1)[0]
        task_obj = task_index.get(task_id)

        if not task_obj:
            logger.warning(f"[BRAIN_DIST] task_id={task_id} not found")
            continue

        if not task_obj.brain_coord:
            continue

        valid_task_cnt += 1

        for l1, l2 in task_obj.brain_coord:
            counter[(l1, l2)] += 1
            total += 1

    logger.debug(
        f"[BRAIN_DIST] valid_tasks={valid_task_cnt}, total_coords={total}"
    )

    # --- 3️⃣ 构建分布 ---
    brain_distribution: List[Dict[str, Any]] = []

    for (l1, l2), count in counter.items():
        brain_distribution.append(
            {
                "l1": int(l1),
                "l2": int(l2),
                "count": int(count),
                "ratio": round(count / total, 3),  # 保留3位小数
            }
        )

    # --- 4️⃣ Level1 汇总 ---
    level1_counter: Dict[int, int] = defaultdict(int)

    for item in brain_distribution:
        level1_counter[item["l1"]] += item["count"]

    level1_distribution = {
        int(k): int(v) for k, v in level1_counter.items()
    }

    # --- 5️⃣ （可选）构建矩阵 ---
    brain_matrix = None

    if build_matrix:
        brain_matrix = [[0 for _ in range(19)] for _ in range(4)]

        for (l1, l2), count in counter.items():
            brain_matrix[l1][l2] = int(count)

    # --- 6️⃣ 写入画像 ---
    enriched_profile["brain_distribution"] = brain_distribution
    enriched_profile["level1_distribution"] = level1_distribution

    if build_matrix:
        enriched_profile["brain_matrix"] = brain_matrix

    logger.debug(
        f"[BRAIN_DIST] build complete for user_id={profile.get('user_id')}"
    )

    return enriched_profile


def enrich_profile_with_user_type(profile: dict) -> dict:
    """
    给用户画像 profile 打上 user_type 标签（写回 profile 并返回）

    规则：
    1. 优势倾向型：存在一级脑能力 ≥ ADVANTAGE_LINE
    2. 潜能倾向型：存在一级脑能力 ∈ [POTENTIAL_LINE, ADVANTAGE_LINE)
    3. 蓄力成长型：
       若不属于以上两类，
       则说明所有一级脑能力数值都 < ADVANTAGE_LINE（如 90）
    """

    level1_scores = profile.get("latest_level1_scores", {})
    level1_values = [v for v in level1_scores.values() if isinstance(v, (int, float))]

    # 默认值：蓄力成长型
    # 此分支意味着：
    # - 不存在一级能力 ≥ ADVANTAGE_LINE
    # - 不存在一级能力 ∈ [POTENTIAL_LINE, ADVANTAGE_LINE)
    # => 所有一级脑能力数值都 < POTENTIAL_LINE
    # => 且必然 < ADVANTAGE_LINE（如 100）
    user_type = UserType.GROWTH
    reason = "所有一级脑能力数值都小于 POTENTIAL_LINE（如 90），划为蓄力成长型"

    # 1️⃣ 优势倾向型
    if any(v >= ScoreThreshold.ADVANTAGE_LINE for v in level1_values):
        user_type = UserType.ADVANTAGE
        reason = "存在一级脑能力 ≥ ADVANTAGE_LINE"

    # 2️⃣ 潜能倾向型
    elif any(
        ScoreThreshold.POTENTIAL_LINE <= v < ScoreThreshold.ADVANTAGE_LINE
        for v in level1_values
    ):
        user_type = UserType.POTENTIAL
        reason = "存在一级脑能力 ∈ [POTENTIAL_LINE, ADVANTAGE_LINE)"

    enriched_profile = dict(profile)  # 浅拷贝，避免污染原对象
    enriched_profile["user_type"] = user_type

    # --- debug 日志 ---
    user_id = profile.get("user_id", "unknown")
    logger.debug(
        f"[ENRICH_PROFILE] user_id={user_id} "
        f"level1_scores={level1_scores} "
        f"user_type={user_type} "
        f"reason={reason}"
    )

    return enriched_profile


def build_user_modules_by_threshold(
    enriched_profile: dict,
    level2_to_level1: Dict[str, str],  # 保留参数避免外部报错，但不再使用
    threshold: int,
    llm: BaseLLM,
    l1_task_map: Dict[int, List[Task]]
) -> List[TrainingModule]:

    level1_scores: Dict[str, int] = enriched_profile.get("latest_level1_scores", {})
    weekly_missed_task_infos: List[Task] = enriched_profile.get(
        "weekly_missed_task_infos", []
    )
    last_day_task_info: Task | None = enriched_profile.get("last_day_task_info")
    user_type: UserType = enriched_profile.get("user_type", UserType.GROWTH)
    user_id = enriched_profile.get("user_id", "unknown")

    top_two: List[str] = []
    balanced: List[str] = []

    # ==============================
    # 计算 top_two / balanced
    # ==============================

    # 1️⃣ 蓄力成长型
    # 规则：
    # 所有一级脑能力都 < POTENTIAL_LINE
    # 因此只做相对排序
    if user_type == UserType.GROWTH:
        sorted_level1 = sorted(
            level1_scores.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        top_two = [ability for ability, _ in sorted_level1[:2]]
        balanced = [ability for ability, _ in sorted_level1[2:]]

    # 2️⃣ 优势倾向型 / 潜能倾向型
    else:
        qualified = [
            (ability, score)
            for ability, score in level1_scores.items()
            if score >= threshold
        ]

        qualified_sorted = sorted(
            qualified,
            key=lambda x: x[1],
            reverse=True,
        )

        top_two = [ability for ability, _ in qualified_sorted[:2]]

        balanced = [
            ability for ability in level1_scores.keys() if ability not in top_two
        ]

    logger.debug(
        f"[BUILD_MODULES] user_id={user_id} user_type={user_type} "
        f"threshold={threshold} top_two={top_two} balanced={balanced}"
    )

    # ==============================
    # 构造训练项
    # ==============================

    def build_training_item(
        level1_key: str,
        score: int,
        suffix: str,
    ) -> TrainingItem | None:

        ability_name_cn = level1_key
        l1_recommended_tasks = l1_task_map[L1_INDEX[level1_key]]

        paradigm_tasks = get_recommended_tasks_grouped_by_paradigm(
            l1_recommended_tasks,
        )

        if not paradigm_tasks:
            raise BizError(
                ErrorCode.TRAINING_TASK_NOT_AVAILABLE,
                user_id=user_id,
                level1_key=level1_key,
            )

        item = TrainingItem(
            name=f"{ability_name_cn}{suffix}",
            tasks=fetch_tasks_by_ability(paradigm_tasks),
            difficulty=calc_difficulty(last_day_task_info, paradigm_tasks),
            frequency=fetch_frequency(paradigm_tasks),
            goal=generate_goal_by_llm(paradigm_tasks, llm),
            description="低压力、高成功体验",
        )

        logger.debug(
            f"[BUILD_TRAINING_ITEM] user_id={user_id} "
            f"level1_key={level1_key} "
            f"name={item.name} "
            f"tasks_count={len(item.tasks)} "
            f"difficulty={item.difficulty} "
            f"frequency={item.frequency}"
        )

        return item

    # ==============================
    # 构造 advantage_items / balanced_items
    # ==============================

    advantage_items = [
        item
        for a in top_two
        if (
            item := build_training_item(
                level1_key=a,
                score=level1_scores.get(a, 0),
                suffix="进阶训练",
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
            )
        )
    ]

    # ==============================
    # 组装模块
    # ==============================

    module_names = USER_TYPE_MODULE_MAP.get(
        user_type,
        USER_TYPE_MODULE_MAP[UserType.GROWTH],
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
            module_name=module_name,
            items=module_items_map.get(module_name, []),
        )
        for module_name in module_names
    ]

    logger.debug(f"[BUILD_MODULES_DONE] user_id={user_id} modules_count={len(modules)}")

    return modules


def build_advantage_user_modules(
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
    l1_task_map: Dict[int, List[Task]]
) -> List[TrainingModule]:
    """
    构建【优势倾向型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.ADVANTAGE_LINE,
        llm=llm,
        l1_task_map=l1_task_map,
    )


def build_potential_user_modules(
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
    l1_task_map: Dict[int, List[Task]]
) -> List[TrainingModule]:
    """
    构建【潜能倾向型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.POTENTIAL_LINE,
        llm=llm,
        l1_task_map=l1_task_map,
    )


def build_special_user_modules(
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
    l1_task_map: Dict[int, List[Task]]
) -> List[TrainingModule]:
    """
    构建【专项优势型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.ADVANTAGE_LINE,
        llm=llm,
        l1_task_map=l1_task_map,
    )


def build_growth_user_modules(
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
    l1_task_map: Dict[int, List[Task]]
) -> List[TrainingModule]:
    """
    构建【蓄力成长型】用户的训练模块结构
    """
    return build_user_modules_by_threshold(
        enriched_profile=enriched_profile,
        level2_to_level1=level2_to_level1,
        threshold=ScoreThreshold.POTENTIAL_LINE,
        llm=llm,   
        l1_task_map=l1_task_map,
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
            "score_prediction": (
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。"
            ),
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
            "score_prediction": (
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。"
            ),
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
            "score_prediction": (
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。"
            ),
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
            "score_prediction": (
                "按照训练方案，每天执行训练任务，预估下一阶段各一级脑力值能会有明显提升。除了做任务，孩子情绪状态也很重要，家长要多关注和陪伴孩子。"
            ),
        },
    }

    return templates.get(profile["user_type"], templates[UserType.GROWTH.value])


def build_features(history: list[float], max_history_len: int) -> dict:
    arr = np.array(history, dtype=float)
    feats = {}

    for i in range(1, max_history_len + 1):
        feats[f'lag_{i}'] = arr[-i] if len(arr) >= i else np.nan

    feats['mean_4'] = arr[-4:].mean() if len(arr) >= 4 else arr.mean()
    feats['mean_12'] = arr[-12:].mean() if len(arr) >= 12 else arr.mean()
    feats['std_12'] = arr[-12:].std() if len(arr) >= 12 else arr.std()
    feats['min'] = arr.min()
    feats['max'] = arr.max()

    if len(arr) >= 2:
        x = np.arange(len(arr))
        feats['trend'] = np.polyfit(x, arr, 1)[0]
    else:
        feats['trend'] = 0.0

    feats['growth_4'] = arr[-1] - arr[-4] if len(arr) >= 4 else 0.0
    feats['growth_12'] = arr[-1] - arr[-12] if len(arr) >= 12 else 0.0
    feats['last'] = arr[-1]
    feats['diff_1'] = arr[-1] - arr[-2] if len(arr) >= 2 else 0.0
    feats['diff_2'] = arr[-2] - arr[-3] if len(arr) >= 3 else 0.0
    feats['diff_last_vs_mean_4'] = arr[-1] - (arr[-4:].mean() if len(arr) >= 4 else arr.mean())
    feats['diff_mean_4_12'] = (arr[-4:].mean() - arr[-12:].mean()) if len(arr) >= 12 else 0.0
    feats['range_4'] = (arr[-4:].max() - arr[-4:].min()) if len(arr) >= 4 else (arr.max() - arr.min())
    feats['range_12'] = (arr[-12:].max() - arr[-12:].min()) if len(arr) >= 12 else (arr.max() - arr.min())
    feats['std_ratio_4_12'] = ((arr[-4:].std() + 1e-6) / (arr[-12:].std() + 1e-6)) if len(arr) >= 12 else 1.0
    feats['trend_4'] = np.polyfit(np.arange(4), arr[-4:], 1)[0] if len(arr) >= 4 else feats['trend']
    feats['trend_8'] = np.polyfit(np.arange(8), arr[-8:], 1)[0] if len(arr) >= 8 else feats['trend']
    feats['last_vs_min'] = arr[-1] - arr.min()
    feats['last_vs_max'] = arr[-1] - arr.max()

    return feats

def compute_M(N, current, range_val, alpha_c=150):
    """
    计算最终修正值 M

    约束：
    - M > current
    - M < 160
    - current 越大 → 增长越保守
    """

    # --- Step 0: 修正 range_val（关键） ---
    range_val = max(range_val, 0.0)

    # --- Step 1: 计算 k ---
    k = compute_alpha(current, c=alpha_c)

    # --- Step 2: 防止预测下降 ---
    # 至少增长一个极小值 or range_val
    min_increase = max(1e-6, range_val)
    N = min(N, current + min_increase)

    # --- Step 3: 上界控制 ---
    max_cap = 160 - 1  # 你这里留了 buffer（很好）

    # 可增长空间
    delta = min(N - current, max_cap - current)

    # --- Step 4: 插值 ---
    M = current + k * delta

    # --- Step 5: 下界保护 ---
    M = max(M, current + 1e-6)

    return M

def compute_alpha(current, c=150, s=10):
    """
    计算权重 k ∈ (0,1)

    参数：
    - current: 当前值
    - c: 拐点（越小越保守）
    - s: 平滑程度（越小下降越快）

    性质：
    - current ↑ → k ↓
    - current → 160 → k → 0
    """
    return 1 / (1 + np.exp((current - c) / s))

def direct_horizon_forecast(
    model,
    history: list[float],
    current: float,
    max_history_len: int,
    feature_cols: list[str],
    alpha_c: float,
) -> float:
    effective_history = history[-max_history_len:]

    feats = build_features(effective_history, max_history_len)
    feats['hist_len'] = len(effective_history)
    feats['current'] = current

    # --- 计算 range ---
    if len(effective_history) > 0:
        range_val = max(effective_history) - min(effective_history)
    else:
        range_val = 0.0

    X = pd.DataFrame([feats]).reindex(columns=feature_cols, fill_value=np.nan)
    pred = float(model.predict(X)[0])
    pred = compute_M(pred, current, range_val, alpha_c=alpha_c)
    return pred

def compute_baseline_prediction(
    history: list[float],
    current: float,
    *,
    horizon_weeks: int = 12,
    min_decay: float = 5,  # 最小下降，防止完全不变
) -> int:
    """
    无任务预测（基于历史波动幅度的下降）

    逻辑：
    - 用历史 max-min 表示波动能力
    - 按 horizon / 历史长度 进行缩放
    - 强制下降
    """

    if not history:
        return int(round(current))

    history_arr = np.array(history, dtype=float)

    # ----------------------
    # Step 1: 波动幅度
    # ----------------------
    range_val = history_arr.max() - history_arr.min()

    # 防止全平（range=0）
    range_val = max(range_val, min_decay)

    # ----------------------
    # Step 2: 历史长度
    # ----------------------
    hist_len = len(history_arr)

    # 防止除0
    hist_len = max(hist_len, 1)

    # ----------------------
    # Step 3: 下降幅度
    # ----------------------
    decay = (horizon_weeks / hist_len) * range_val

    # 控制最小下降
    decay = max(decay, min_decay)

    # ----------------------
    # Step 4: 计算 baseline
    # ----------------------
    baseline = current - decay

    # ----------------------
    # Step 5: 约束
    # ----------------------
    baseline = min(baseline, current)  # 必须下降
    baseline = max(baseline, 0)        # 下界

    return int(round(baseline))


def build_score_prediction(
    profile: dict,
    fixed_templates: dict,
    model_manager: ModelManager,
    config: Dict[str, Any],
) -> ScorePrediction:
    level1_scores = profile.get("latest_level1_scores", {})
    score_prediction_config = config.get("score_prediction", {})
    max_history_len = int(score_prediction_config.get("max_history_len", 20))
    alpha_c = float(score_prediction_config.get("alpha_c", 150))
    lightgbm_config = score_prediction_config.get("lightgbm", {})
    feature_columns_path = Path(
        lightgbm_config.get(
            "feature_columns",
            "checkpoints/cognitive_l1/feature_columns.json",
        )
    )

    if not feature_columns_path.exists():
        raise FileNotFoundError(
            f"Feature columns file not found: {feature_columns_path}"
        )

    with open(feature_columns_path, "r", encoding="utf-8") as f:
        feature_columns_map = json.load(f)

    def build_dim(level1_key: str) -> DimensionScorePrediction:
        history_seq = profile.get("domain_histories", {}).get(level1_key, [])
        model_key = LEVEL1_DOMAIN_KEY_MAP[level1_key]
        feature_cols = feature_columns_map.get(model_key)

        if len(history_seq) < 2:
            raise ValueError(f"Insufficient history for domain: {level1_key}")

        if not feature_cols:
            raise ValueError(f"Missing feature columns for domain: {model_key}")

        current = float(history_seq[-1])
        history = history_seq[:-1]

        historical = int(level1_scores.get(level1_key, current))
        baseline_predicted = compute_baseline_prediction(history, current)
        predicted = direct_horizon_forecast(
            model=model_manager.get(model_key),
            history=history,
            current=current,
            max_history_len=max_history_len,
            feature_cols=feature_cols,
            alpha_c=alpha_c,
        )

        predicted = Level1Score.clamp(predicted)
        predicted = int(round(predicted))

        return DimensionScorePrediction(
            historical_score=historical,
            predicted_score=predicted,
            baseline_predicted_score=baseline_predicted,
        )

    return ScorePrediction(
        summary=fixed_templates["score_prediction"],
        attention=build_dim(Level1BrainDomain.ATTENTION.value),
        memory=build_dim(Level1BrainDomain.MEMORY.value),
        executive_control=build_dim(Level1BrainDomain.EXECUTIVE.value),
        perception=build_dim(Level1BrainDomain.PERCEPTION.value),
    )

def build_l1_task_map(recommended_tasks: List[Task]) -> Dict[int, List[Task]]:
    """
    构建：
    {
        l1_index: [Task, Task, ...]  # 去重
    }
    """

    l1_task_map: Dict[int, Dict[str, Task]] = {}

    for task in recommended_tasks:

        # 跳过无效
        if task.l1_index is None:
            continue

        l1 = task.l1_index

        # 初始化
        if l1 not in l1_task_map:
            l1_task_map[l1] = {}

        # ✅ 用 task_id 去重
        l1_task_map[l1][task.task_id] = task

    # ✅ 转成 List[Task]
    result: Dict[int, List[Task]] = {
        l1: list(task_dict.values())
        for l1, task_dict in l1_task_map.items()
    }

    return result

# ===============================
# 1️⃣ 构建目标分布矩阵
# ===============================
def build_simple_target_matrix(
    profile: Dict[str, Any],
    brain_distribution: List[Dict[str, Any]],
) -> np.ndarray:
    """
    构建 4x19 目标矩阵
    """

    matrix = np.zeros((len(Level1BrainDomain), len(Level2BrainDomain)))  # 4x19 矩阵

    # --- 1. L1弱项权重 ---
    l1_scores = profile["latest_level1_scores"]  
    max_score = max(l1_scores.values())

    l1_weight = {
        L1_INDEX[k]: max_score - v + 1
        for k, v in l1_scores.items()
        if k in L1_INDEX
    }

    # --- 2. 历史分布 ---
    history = {
        (item["l1"], item["l2"]): item["ratio"]
        for item in brain_distribution
    }

    # --- 3. 填充矩阵 ---
    for l1 in range(len(Level1BrainDomain)):
        for l2 in range(len(Level2BrainDomain)):
            penalty = 1 - history.get((l1, l2), 0)
            matrix[l1][l2] = l1_weight.get(l1, 1) * penalty

    # --- 4. 归一化 ---
    total = matrix.sum()
    if total > 0:
        matrix = matrix / total

    return matrix

# ===============================
# 2️⃣ task打分
# ===============================
def score_task(task, target_matrix: np.ndarray) -> float:
    """
    task: 你的 Task 对象（必须有 brain_coord）
    """

    if not task.brain_coord:
        return 0.0

    return sum(
        target_matrix[l1][l2]
        for l1, l2 in task.brain_coord
    )


# ===============================
# 3️⃣ 推荐任务
# ===============================
def recommend_tasks(
    task_list: List[Task],
    target_matrix: np.ndarray,
    k: int = 420,
) -> List[Task]:
    """
    按权重随机推荐任务
    """

    scores = []

    for task in task_list:
        s = score_task(task, target_matrix)

        # 防止全0
        scores.append(max(s, 1e-6))

    return random.choices(task_list, weights=scores, k=k)


def build_l2_distribution_from_tasks(
    tasks: List[Task],
) -> List[Dict[str, Any]]:
    """
    统计推荐任务中的二级脑能力分布
    返回：[{name, count, ratio}]
    """

    counter = defaultdict(int)
    total = 0

    for task in tasks:
        if task.l2_index is None:
            continue

        counter[task.l2_index] += 1
        total += 1

    if total == 0:
        return []

    result = []

    for l2_idx, count in counter.items():
        result.append({
            "name": L2_INDEX_REVERSE.get(l2_idx, f"unknown_{l2_idx}"),
            "count": int(count),
            "ratio": round(count / total, 3)  # ✅ 保留3位小数
        })

    # ✅ 可选：按占比排序
    result.sort(key=lambda x: x["ratio"], reverse=True)

    return result


def build_L2_brain_ability_treemap(
    profile: Dict[str, Any],
    task_repo: Dict[str, Any],
    k: int = 420,
) -> Tuple[List[Task], List[L2AbilityStat]]:
    """
    返回：
    {
        "recommended_tasks": List[Task],
        "l2_stats": List[L2AbilityStat]
    }
    """

    task_list = task_repo["task_list"]

    brain_distribution = profile.get("brain_distribution")
    if not brain_distribution:
        raise ValueError("brain_distribution 不能为空")

    # 1️⃣ 目标矩阵
    target_matrix = build_simple_target_matrix(
        profile, brain_distribution
    )

    # 2️⃣ 推荐任务
    recommended_tasks = recommend_tasks(
        task_list,
        target_matrix,
        k=k,
    )

    # 3️⃣ 统计 L2 分布（dict）
    l2_distribution = build_l2_distribution_from_tasks(
        recommended_tasks
    )

    # ✅ 4️⃣ 直接转成 Pydantic 对象
    l2_stats: List[L2AbilityStat] = [
        L2AbilityStat(**item)
        for item in l2_distribution
    ]

    return recommended_tasks, l2_stats


def validate_recommendation_performance(
    profile: Dict[str, Any],
    recommended_tasks: List[Task],
    top_n_targets: int = 5,
) -> Dict[str, Any]:
    """
    验证推荐结果对目标矩阵高权重坐标的命中情况。

    命中率定义：
    - hit_rate: 推荐结果中，brain_coord 命中目标矩阵 Top N 坐标的占比
    - unique_hit_rate: 去重后 task_id 维度的命中占比
    """

    brain_distribution = profile.get("brain_distribution")
    if not brain_distribution:
        return {}

    target_matrix = build_simple_target_matrix(profile, brain_distribution)

    ranked_targets: List[Tuple[Tuple[int, int], float]] = sorted(
        [
            ((l1_idx, l2_idx), float(target_matrix[l1_idx][l2_idx]))
            for l1_idx in range(target_matrix.shape[0])
            for l2_idx in range(target_matrix.shape[1])
        ],
        key=lambda item: item[1],
        reverse=True,
    )

    top_n_targets = max(int(top_n_targets), 1)
    target_coords = [coord for coord, _ in ranked_targets[:top_n_targets]]
    target_coord_set = set(target_coords)

    total_count = len(recommended_tasks)
    if total_count == 0:
        metrics = {
            "top_n_targets": top_n_targets,
            "target_coords": [],
            "total_count": 0,
            "hit_count": 0,
            "hit_rate": 0.0,
            "unique_task_count": 0,
            "unique_hit_count": 0,
            "unique_hit_rate": 0.0,
        }
        logger.info("[RECOMMENDATION_VALIDATION] %s", metrics)
        return metrics

    def is_hit(task: Task) -> bool:
        if not task.brain_coord:
            return False
        return any(tuple(coord) in target_coord_set for coord in task.brain_coord)

    hit_count = sum(1 for task in recommended_tasks if is_hit(task))

    unique_tasks: Dict[str, Task] = {}
    for task in recommended_tasks:
        unique_tasks[task.task_id] = task

    unique_hit_count = sum(1 for task in unique_tasks.values() if is_hit(task))

    metrics = {
        "top_n_targets": top_n_targets,
        "target_coords": [
            {
                "l1": L1_INDEX_REVERSE.get(l1_idx, str(l1_idx)),
                "l2": L2_INDEX_REVERSE.get(l2_idx, str(l2_idx)),
                "weight": round(weight, 6),
            }
            for (l1_idx, l2_idx), weight in ranked_targets[:top_n_targets]
        ],
        "total_count": total_count,
        "hit_count": hit_count,
        "hit_rate": round(hit_count / total_count, 4),
        "unique_task_count": len(unique_tasks),
        "unique_hit_count": unique_hit_count,
        "unique_hit_rate": round(
            unique_hit_count / len(unique_tasks), 4
        ) if unique_tasks else 0.0,
    }

    logger.info("[RECOMMENDATION_VALIDATION] %s", metrics)

    return metrics



def render_plan_text(plan: AIRecPlanData) -> str:
    lines = []

    # 1️⃣ 开篇
    lines.append("1）开篇文案概述")
    lines.append(plan.overview)
    lines.append("")

    # 2️⃣ 训练计划
    lines.append("2）AI推荐训练计划内容展示")
    lines.append(plan.training_plan_intro)
    lines.append("")

    for idx, module in enumerate(plan.modules, 1):
        lines.append(f"{idx}. {module.module_name}")

        for sub_idx, item in enumerate(module.items):
            letter = chr(97 + sub_idx)  # a,b,c,d

            lines.append(f"    {letter}. {item.name}")
            lines.append(f"    任务名称：{item.tasks}")
            lines.append(f"    训练频次：{item.frequency}")
            lines.append(f"    训练目标：{item.goal}")
            lines.append("")

    # ✅ 3️⃣ 二级脑能力分布（新增）
    if plan.l2_ability_distribution:
        lines.append("3）训练能力分布说明")
        lines.append("本阶段训练将重点覆盖以下脑能力：")

        for item in plan.l2_ability_distribution:
            percent = round(item.ratio * 100, 1)
            lines.append(
                f"- {item.name}：{item.count}次（占比 {percent}%）"
            )

        lines.append("")

    # 4️⃣ 分数预测（序号顺延）
    sp = plan.score_prediction
    lines.append("4）AI分数预测")
    lines.append(sp.summary)
    lines.append("")

    lines.append(
        f"注意力完成度：{sp.attention.historical_score} → {sp.attention.predicted_score}（无训练：{sp.attention.baseline_predicted_score}）"
    )
    lines.append(
        f"记忆力完成度：{sp.memory.historical_score} → {sp.memory.predicted_score}（无训练：{sp.memory.baseline_predicted_score}）"
    )
    lines.append(
        f"执行控制完成度：{sp.executive_control.historical_score} → {sp.executive_control.predicted_score}（无训练：{sp.executive_control.baseline_predicted_score}）"
    )
    lines.append(
        f"感知觉完成度：{sp.perception.historical_score} → {sp.perception.predicted_score}（无训练：{sp.perception.baseline_predicted_score}）"
    )

    lines.append("")
    lines.append("▲预测数据仅供参考，以孩子最终训练数据为准")
    lines.append("")

    # 5️⃣ 居家建议
    lines.append("5）居家训练建议")
    for advice in plan.home_advice:
        lines.append(f"- {advice}")
    lines.append("")

    # 6️⃣ 效果追踪
    lines.append("6）效果追踪与动态调整")
    for item in plan.tracking_and_adjustment:
        lines.append(item)

    return "\n".join(lines)
