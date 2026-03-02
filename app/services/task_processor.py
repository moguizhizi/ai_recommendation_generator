# app/services/task_processor.py
from typing import Dict, List

from app.schemas.common import Task


def build_level2_to_level1_map(task_info: Dict) -> Dict[str, str]:
    """
    根据 task_info 中的 tasks 构建 level2_brain -> level1_brain 映射

    返回示例：
    {
        "记忆力-工作记忆": "记忆力",
        "记忆力-空间记忆": "记忆力",
    }
    """

    level2_to_level1: Dict[str, str] = {}

    tasks = task_info.get("tasks", [])

    for task in tasks:
        level1 = task.get("level1_brain")
        level2_raw = task.get("level2_brain")

        if not level1 or not level2_raw:
            continue

        # 可能是： "记忆力-工作记忆,记忆力-空间记忆"
        level2_list = [x.strip() for x in level2_raw.split(",") if x.strip()]

        for level2 in level2_list:
            # 如果存在冲突，可以选择忽略、覆盖、或报警
            level2_to_level1[level2] = level1

    return level2_to_level1


def process_task_info(profile: dict, raw_task_info: dict) -> dict:
    """
    对外部任务数据做本地清洗与增强处理：
    - 按能力分组 perception / exec / attention / memory
    - 提取 last_task 的 difficulty
    - 提取 weekly_missed_tasks 的 difficulty / life_desc / duration
    - 提取一级脑能力 / 二级脑能力
    """

    tasks = raw_task_info.get("tasks", [])

    # --- 1️⃣ 按能力分组 ---
    grouped = {"perception": [], "exec": [], "attention": [], "memory": []}

    # --- 2️⃣ 构建 task_id -> task_info 的索引 ---
    task_index = {}
    for t in tasks:
        task_id = t.get("id")
        if task_id:
            task_index[task_id] = t

        ability = t.get("ability")
        if ability in grouped:
            grouped[ability].append(t)

    # --- 3️⃣ 处理 last_task ---
    last_task_info = None
    last_task = profile.get("last_task")
    if last_task:
        last_task_id = last_task.get("id")
        raw_task = task_index.get(last_task_id)

        if raw_task:
            last_task_info = {
                "id": last_task_id,
                "name": raw_task.get("name"),
                "difficulty": raw_task.get("difficulty"),
            }

    # --- 4️⃣ 处理 weekly_missed_tasks ---
    missed_task_infos: List[Task] = []

    for missed in profile.get("weekly_missed_tasks", []):
        task_id = missed.get("id")
        raw_task = task_index.get(task_id)

        if not raw_task:
            continue

        missed_task_infos.append(
            Task(
                id=task_id,
                name=raw_task.get("name"),
                difficulty=raw_task.get("difficulty"),
                life_desc=raw_task.get("life_desc"),
                paradigm=raw_task.get("paradigm"),
                duration_min=raw_task.get("duration_min"),
                level1_brain=raw_task.get("level1_brain"),
                level2_brain=raw_task.get("level2_brain"),
            )
        )

    return {
        "grouped_tasks": grouped,
        "last_task_info": last_task_info,
        "weekly_missed_task_infos": missed_task_infos,
    }
