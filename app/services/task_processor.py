# app/services/task_processor.py
from typing import Dict, List

from app.schemas.common import Task
from collections import defaultdict


def build_level2_to_level1_map(task_repo: Dict) -> Dict[str, str]:
    """
    根据 task_repo 构建 level2_brain -> level1_brain 映射

    返回示例：
    {
        "记忆力-工作记忆": "记忆力",
        "记忆力-空间记忆": "记忆力",
    }
    """

    level2_to_level1: Dict[str, str] = {}

    # task_repo 中已经是 Task 对象了
    task_list = task_repo.get("task_list", [])

    for task in task_list:
        level1 = task.level1_brain
        level2_list = task.level2_brain  # 已经是 List[str]

        if not level1 or not level2_list:
            continue

        for level2 in level2_list:

            if level2 not in level2_to_level1:
                level2_to_level1[level2] = level1

    return level2_to_level1


def build_task_repository(raw_task_info: dict) -> dict:
    """
    构建系统级 Task 仓库（与用户无关）
    """
    raw_tasks = raw_task_info.get("tasks", [])

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

    task_index = {t.id: t for t in task_list if t.id is not None}

    level1_grouped = defaultdict(list)
    level2_grouped = defaultdict(list)

    for task in task_list:
        if task.level1_brain:
            level1_grouped[task.level1_brain].append(task)

        for level2 in task.level2_brain:
            level2_grouped[level2].append(task)

    return {
        "task_list": task_list,
        "task_index": task_index,
        "level1_grouped_tasks": dict(level1_grouped),
        "level2_grouped_tasks": dict(level2_grouped),
    }
