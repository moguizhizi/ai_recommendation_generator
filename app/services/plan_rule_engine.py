# app/services/plan_rule_engine.py
import random
from app.core.constants import ModuleName, UserType, ScoreThreshold
from typing import Dict, List, Tuple
from collections import defaultdict
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import BizError
from app.schemas.chat import (
    AIRecPlanData,
    DimensionScorePrediction,
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
    get_missed_tasks_grouped_by_paradigm,
)
from llm.base import BaseLLM

from utils.logger import get_logger
from models.model_factory import ModelManager

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

        paradigm_tasks = get_missed_tasks_grouped_by_paradigm(
            level1_key,
            weekly_missed_task_infos,
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
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
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
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
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
    enriched_profile: dict,
    level2_to_level1: dict,
    llm: BaseLLM,
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


def simple_predict(score: float) -> float:
    if score < 60:
        return score + 5
    elif score < 80:
        return score + 3
    else:
        return score + 1


def build_score_prediction(
    profile: dict, fixed_templates: dict, model_manager: ModelManager
) -> ScorePrediction:
    level1_scores = profile.get("latest_level1_scores", {})

    def build_dim(key: str) -> DimensionScorePrediction:
        historical = float(level1_scores.get(key, 0))
        predicted = simple_predict(historical)

        return DimensionScorePrediction(
            historical_score=historical,
            predicted_score=predicted,
        )

    return ScorePrediction(
        summary=fixed_templates["score_prediction"],
        attention=build_dim("注意力"),
        memory=build_dim("记忆力"),
        executive_control=build_dim("执行控制"),
        perception=build_dim("感知觉"),
    )


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
            lines.append(f"        任务：{item.tasks}")
            lines.append(f"        难度：{item.difficulty}")
            lines.append(f"        频次：{item.frequency}")
            lines.append(f"        目标：{item.goal}")

            # if item.description:
            #     lines.append(f"        说明：{item.description}")

            lines.append("")

    # 3️⃣ 分数预测
    sp = plan.score_prediction
    lines.append("3）AI分数预测")
    lines.append(sp.summary)
    lines.append("")

    lines.append(
        f"注意力完成度：{sp.attention.historical_score} → {sp.attention.predicted_score}"
    )
    lines.append(
        f"记忆力完成度：{sp.memory.historical_score} → {sp.memory.predicted_score}"
    )
    lines.append(
        f"执行控制完成度：{sp.executive_control.historical_score} → {sp.executive_control.predicted_score}"
    )
    lines.append(
        f"感知觉完成度：{sp.perception.historical_score} → {sp.perception.predicted_score}"
    )

    lines.append("")
    lines.append("▲预测数据仅供参考，以孩子最终训练数据为准")
    lines.append("")

    # 4️⃣ 居家建议
    lines.append("4）居家训练建议")
    for advice in plan.home_advice:
        lines.append(f"- {advice}")
    lines.append("")

    # 5️⃣ 效果追踪
    lines.append("5）效果追踪与动态调整")
    for item in plan.tracking_and_adjustment:
        lines.append(item)

    return "\n".join(lines)
