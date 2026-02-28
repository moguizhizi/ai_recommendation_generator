from typing import Dict, List, Optional
from collections import defaultdict
import random

from app.schemas.common import Task


def get_missed_tasks_grouped_by_paradigm(
    ability_key: str, task_info: Dict
) -> Dict[str, List[Task]]:
    """
    本地接口：根据能力类型，从 task_info.weekly_missed_task_infos 中匹配训练范式（paradigm + task）

    返回结构：
    {
        "长度知觉任务": [task1, task2],
        "no_paradigm": [task1, task2]
    }

    规则：
    1. ability_key 匹配 level1_brain 或 level2_brain
    2. 按 paradigm 分组
    3. 无 paradigm 的 task 统一放入 no_paradigm
    """

    missed_tasks: List[Task] = task_info.get("weekly_missed_task_infos", [])

    paradigm_tasks: Dict[str, List[Task]] = defaultdict(list)

    for t in missed_tasks:
        if not t.name:
            continue

        # ability_key 匹配一级或二级脑能力
        if t.level1_brain != ability_key and ability_key not in (t.level2_brain or []):
            continue

        # 没有范式的统一归类
        paradigm = t.paradigm or "no_paradigm"
        paradigm_tasks[paradigm].append(t)

    return dict(paradigm_tasks)


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
    last_task: Optional[Task], paradigm_tasks: Dict[str, List[Task]]
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

    if not last_task or not isinstance(last_task.difficulty, (int, float)):
        return DEFAULT

    base = float(last_task.difficulty)

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
            if isinstance(task.duration_min, (int, float)) and task.duration_min > 0:
                durations.append(int(task.duration_min))

    # --- 无有效时长兜底 ---
    if not durations:
        return "每日1次，每次4-8分钟"

    durations.sort()

    # --- 只有一个时长 ---
    if len(durations) == 1:
        return f"每日1次，每次{durations[0]}分钟"

    # --- 多个时长，取区间 ---
    return f"每日1次，每次{durations[0]}-{durations[-1]}分钟"


def generate_goal_by_llm(paradigm_tasks: Dict[str, List[Task]]) -> str:
    """
    调用大模型生成训练目标
    """
    return f""
