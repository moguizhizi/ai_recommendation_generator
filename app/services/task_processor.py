# app/services/task_processor.py
from typing import Dict, List

from app.schemas.common import Task
from collections import defaultdict


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

    - 构建 task_index（id -> Task）
    - 按一级脑能力分组 grouped_tasks（Task 对象）
    - 按二级脑能力分组 level2_grouped_tasks（Task 对象）
    - 提取 last_task 的 difficulty
    - 提取 weekly_missed_task_infos（Task 对象）
    """

    raw_tasks = raw_task_info.get("tasks", [])

    # --- 1️⃣ 统一封装 Task 对象 ---
    task_list: List[Task] = []
    for t in raw_tasks:
        task_list.append(
            Task(
                id=t.get("id"),
                name=t.get("name"),
                difficulty=t.get("difficulty"),
                life_desc=t.get("life_desc"),
                paradigm=t.get("paradigm"),
                duration_min=t.get("duration_min"),
                level1_brain=t.get("level1_brain"),
                level2_brain=[
                    x.strip()
                    for x in (t.get("level2_brain") or "").split(",")
                    if x.strip()
                ],
            )
        )

    # --- 2️⃣ 建立 task_index ---
    task_index: Dict[int, Task] = {t.id: t for t in task_list if t.id is not None}

    # --- 3️⃣ 按 level1 / level2 分组 ---
    level1_grouped_tasks: Dict[str, List[Task]] = defaultdict(list)
    level2_grouped_tasks: Dict[str, List[Task]] = defaultdict(list)

    for task in task_list:
        if task.level1_brain:
            level1_grouped_tasks[task.level1_brain].append(task)

        for level2 in task.level2_brain:
            level2_grouped_tasks[level2].append(task)

    # --- 4️⃣ 处理 last_task ---
    last_task_info = None
    last_task = profile.get("last_task")
    if last_task:
        last_task_id = last_task.get("id")
        task_obj = task_index.get(last_task_id)

        if task_obj:
            last_task_info = {
                "id": task_obj.id,
                "name": task_obj.name,
                "difficulty": task_obj.difficulty,
            }

    # --- 5️⃣ 处理 weekly_missed_tasks ---
    missed_task_infos: List[Task] = []

    for missed in profile.get("weekly_missed_tasks", []):
        task_id = missed.get("id")
        task_obj = task_index.get(task_id)
        if task_obj:
            missed_task_infos.append(task_obj)

    return {
        "level1_grouped_tasks": dict(level1_grouped_tasks),  # Dict[str, List[Task]]
        "level2_grouped_tasks": dict(level2_grouped_tasks),  # Dict[str, List[Task]]
        "last_task_info": last_task_info,
        "weekly_missed_task_infos": missed_task_infos,  # List[Task]
    }
