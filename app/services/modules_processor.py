from typing import Dict, List
from collections import defaultdict
import random


def get_missed_tasks_grouped_by_paradigm(
    ability_key: str, task_info: Dict
) -> Dict[str, List[str]]:
    """
    本地接口：根据能力类型，从 task_info.weekly_missed_task_infos 中匹配训练范式（paradigm + task_name）

    返回结构：
    {
        "长度知觉任务": ["小马过河", "测距打鼠"],
        "no_paradigm": ["任务A", "任务B"]
    }

    规则：
    1. ability_key 匹配 level1_brain 或 level2_brain
    2. 按 paradigm 分组
    3. 无 paradigm 的 task 统一放入 no_paradigm
    """

    missed_tasks = task_info.get("weekly_missed_task_infos", [])

    # paradigm -> [task_name1, task_name2, ...]
    paradigm_tasks: Dict[str, List[str]] = defaultdict(list)

    for t in missed_tasks:
        task_name = t.get("name")
        paradigm = t.get("paradigm")

        if not task_name:
            continue

        # ability_key 匹配一级或二级脑能力
        if (
            t.get("level1_brain") != ability_key
            and t.get("level2_brain") != ability_key
        ):
            continue

        # 没有范式的统一归类
        if not paradigm:
            paradigm_tasks["no_paradigm"].append(task_name)
        else:
            paradigm_tasks[paradigm].append(task_name)

    return dict(paradigm_tasks)


def fetch_tasks_by_ability(paradigm_tasks: Dict[str, List[str]]) -> str:
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
        task_str = "、".join(picked_tasks)
        return f"{paradigm}（{task_str}）"

    # --- 2️⃣ 兜底：无范式 ---
    no_paradigm_tasks = paradigm_tasks.get("no_paradigm", [])
    if no_paradigm_tasks:
        picked_tasks = no_paradigm_tasks[:2]
        task_str = "、".join(picked_tasks)
        return f"{task_str}等任务"

    return ""


def calc_difficulty(task_info: Dict) -> str:
    """
    本地规则：计算训练难度
    """
    return "当前能力层级+0.5~1级"


def fetch_frequency(task_info: Dict) -> str:
    """
    本地接口：根据 task_info 中的训练时长，生成训练频次文案

    规则：
    - 从 weekly_missed_task_infos 中提取 duration_min
    - 按时长排序
    - 组装为：每日1次，每次X-Y分钟 / 每次X分钟
    """

    missed_tasks = task_info.get("weekly_missed_task_infos", [])

    durations: List[int] = [
        t.get("duration_min")
        for t in missed_tasks
        if isinstance(t.get("duration_min"), (int, float)) and t.get("duration_min") > 0
    ]

    if not durations:
        return "每日1次，每次4-8分钟"

    durations.sort()

    if len(durations) == 1:
        return f"每日1次，每次{durations[0]}分钟"

    return f"每日1次，每次{durations[0]}-{durations[-1]}分钟"


def generate_goal_by_llm(ability_name_cn: str) -> str:
    """
    调用大模型生成训练目标
    """
    return f"强化{ability_name_cn}能力，提升整体认知灵活性与稳定性。"
