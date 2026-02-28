from typing import Dict, List
from collections import defaultdict


def fetch_tasks_by_ability(ability_key: str, task_info: Dict) -> str:
    """
    本地接口：根据能力类型，从 task_info.weekly_missed_task_infos 中匹配训练范式（paradigm + task_name）

    规则：
    1. ability_key 需匹配 level1_brain 或 level2_brain
    2. 按 paradigm 分组
    3. 同一个 paradigm 最多取 2 个 task
    4. 返回格式：范式（task1、task2），多个范式用中文顿号拼接
       例：长度知觉任务（小马过河、测距打鼠）、多感官协同匹配（找不同）
    """

    missed_tasks = task_info.get("weekly_missed_task_infos", [])

    # paradigm -> [task_name1, task_name2]
    paradigm_tasks: Dict[str, List[str]] = defaultdict(list)

    for t in missed_tasks:
        paradigm = t.get("paradigm")
        task_name = t.get("name")

        if not paradigm or not task_name:
            continue

        # ability_key 匹配一级或二级脑能力
        if (
            t.get("level1_brain") != ability_key
            and t.get("level2_brain") != ability_key
        ):
            continue

        # 同一个范式最多取 2 个 task
        if len(paradigm_tasks[paradigm]) >= 2:
            break

        paradigm_tasks[paradigm].append(task_name)

    # --- 组装展示字符串 ---
    results: List[str] = []
    for paradigm, task_names in paradigm_tasks.items():
        task_str = "、".join(task_names)
        results.append(f"{paradigm}（{task_str}）")

    return "、".join(results)


def calc_difficulty(ability_key: str, score: int) -> str:
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
