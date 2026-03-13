from typing import Dict, List, Optional
from collections import defaultdict
import random

from app.schemas.common import Task
from llm.base import BaseLLM
from app.prompts.plan_prompt import GoalSummaryPrompt


def get_missed_tasks_grouped_by_paradigm(
    level1_key: str,
    weekly_missed_task_infos: List[Task],
    level2_keys: List[str] | None = None,
) -> Dict[str, List[Task]]:
    """
    按范式分组漏训任务
    - level1_key: 一级脑能力 key
    - level2_keys: 可选
    """

    filtered_tasks: List[Task] = []

    for task in weekly_missed_task_infos:
        if task.cognitive_domain != level1_key:
            continue

        filtered_tasks.append(task)

    grouped = defaultdict(list)
    for task in filtered_tasks:
        grouped[task.paradigm].append(task)

    return dict(grouped)


def fetch_tasks_by_ability(paradigm_tasks: Dict[str, List[Task]]) -> str:
    """
    将 paradigm_tasks 组装为展示字符串

    规则：
    1. 若存在有 paradigm 的项 → 随机选 1 个范式，最多 2 个 task，直接返回
    2. 若不存在任何 paradigm → 使用 no_paradigm 组装返回（最多 2 个）
    """

    # --- 1️⃣ 收集所有有范式且有任务的 ---
    valid_paradigms = [
        (paradigm, tasks)
        for paradigm, tasks in paradigm_tasks.items()
        if paradigm != "no_paradigm" and tasks
    ]

    if valid_paradigms:
        paradigm, tasks = random.choice(valid_paradigms)
        picked_tasks = tasks[:2]

        task_names = [t.name for t in picked_tasks if t.name]
        if task_names:
            task_str = "、".join(task_names)
            return f"{paradigm}（{task_str}）"

    # --- 2️⃣ 兜底：无范式 ---
    no_paradigm_tasks = paradigm_tasks.get("no_paradigm", [])
    if no_paradigm_tasks:
        picked_tasks = no_paradigm_tasks[:2]
        task_names = [t.name for t in picked_tasks if t.name]
        if task_names:
            task_str = "、".join(task_names)
            return f"{task_str}等任务"

    return ""


def calc_difficulty(
    last_day_task_info: Optional[Task], paradigm_tasks: Dict[str, List[Task]]
) -> str:
    """
    本地规则：根据历史任务难度 + 本次推荐任务难度区间，生成训练难度文案

    规则：
    1. 从 paradigm_tasks 中筛选 difficulty > last_task.difficulty 的任务
    2. 计算难度差值区间（min_diff ~ max_diff）
    3. 映射为：当前能力层级 + min_diff ~ max_diff 级
    4. 若 last_task 或 difficulty 缺失 → 使用默认兜底文案
    """

    DEFAULT = "当前能力层级+0.5~1级"

    if not last_day_task_info or not isinstance(
        last_day_task_info.difficulty, (int, float)
    ):
        return DEFAULT

    base = float(last_day_task_info.difficulty)

    diffs: List[float] = []

    for tasks in paradigm_tasks.values():
        for task in tasks:
            if isinstance(task.difficulty, (int, float)) and task.difficulty > base:
                diffs.append(round(task.difficulty - base, 1))

    # --- 没有比上一次更高的难度，兜底 ---
    if not diffs:
        return DEFAULT

    diffs.sort()
    min_diff, max_diff = diffs[0], diffs[-1]

    # --- 只提升一个等级 ---
    if min_diff == max_diff:
        return f"当前能力层级+{min_diff}级"

    return f"当前能力层级+{min_diff}~{max_diff}级"


def fetch_frequency(paradigm_tasks: Dict[str, List[Task]]) -> str:
    """
    本地接口：根据已匹配的任务列表，生成训练频次文案

    规则：
    - 从 paradigm_tasks 中提取所有 Task.duration_min
    - 过滤无效 / 非正数时长
    - 按时长升序排序
    - 组装为：
        - 1 个值 → 每日1次，每次 X 分钟
        - 多个值 → 每日1次，每次 X-Y 分钟
    - 若无有效时长 → 使用默认兜底文案
    """

    durations: List[int] = []

    for tasks in paradigm_tasks.values():
        for task in tasks:
            if isinstance(task.max_duration, (int, float)) and task.max_duration > 0:
                durations.append(int(task.max_duration))

    # --- 无有效时长兜底 ---
    if not durations:
        return "每日1次，每次4-8分钟"

    durations.sort()

    # --- 只有一个时长 ---
    if len(durations) == 1:
        return f"每日1次，每次{durations[0]}分钟"

    # --- 多个时长，取区间 ---
    return f"每日1次，每次{durations[0]}-{durations[-1]}分钟"


def generate_goal_by_llm(paradigm_tasks: Dict[str, List[Task]], llm: BaseLLM) -> str:
    """
    根据不同训练范式下的任务 life_desc，总结生成整体训练目标
    """

    # 1️⃣ 收集 life_desc
    life_desc_list = []

    for paradigm, tasks in paradigm_tasks.items():
        for task in tasks:
            if task.life_interpretation:
                life_desc_list.append(
                    f"- [{paradigm}] {task.task_name}: {task.life_interpretation}"
                )

    # 如果没有可用描述，直接返回默认值
    if not life_desc_list:
        return "提升综合认知能力与生活应用能力"

    life_desc_text = "\n".join(life_desc_list)

    # 2️⃣ 构建 Prompt
    prompt = GoalSummaryPrompt.render(life_desc_text=life_desc_text)

    # 3️⃣ 直接调用传入的 llm
    try:
        response = llm.chat(prompt)
    except Exception:
        # 如果 LLM 调用失败，返回默认目标
        return "提升综合认知能力与生活应用能力"

    if not response:
        return "提升综合认知能力与生活应用能力"

    return response.strip()
