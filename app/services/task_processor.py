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


def enrich_user_profile_with_tasks(profile: dict, task_repo: dict) -> dict:
    """
    基于原始 profile + 任务仓库 task_repo，对用户画像做一次「任务视图增强」：

    ✅ 输入 profile（原始结构示例）：
    {
        "train_days": 10,
        "disease_tag": "...",
        "level1_scores": {...},
        "level2_scores": {...},
        "last_task": {"id": 1, "name": "小马过河"},                 # 仅有轻量信息
        "weekly_missed_tasks": [{"id": 2, "name": "小马过河"}, ...] # 仅有轻量信息
    }

    ✅ 输出 enriched_profile（增强后结构）：
    {
        "train_days": 10,
        "disease_tag": "...",
        "level1_scores": {...},
        "level2_scores": {...},

        # 🚀 替换为完整 Task 视图
        "last_task_info": Task | None,              # 最近一次训练任务（完整 Task 对象）
        "weekly_missed_task_infos": List[Task],     # 过去一周漏训任务（完整 Task 对象列表）
    }

    设计目标：
    - profile 中不再保留 last_task / weekly_missed_tasks（轻量 id 结构）
    - 统一对外暴露 Task 对象，方便后续做难度、频次、范式等业务逻辑处理
    - 保证 profile 结构「干净、单一事实来源」
    """

    task_index: Dict[int, Task] = task_repo["task_index"]

    # 浅拷贝一份 profile，避免污染原始入参（上游数据源可能复用 profile）
    enriched_profile = dict(profile)

    # --- 1️⃣ last_task -> last_task_info（直接升级为 Task 对象） ---
    last_task_info = None
    last_task = profile.get("last_task")
    if last_task:
        task_obj = task_index.get(last_task.get("id"))
        if task_obj:
            last_task_info = task_obj

    # --- 2️⃣ weekly_missed_tasks -> weekly_missed_task_infos（升级为 Task 列表） ---
    missed_task_infos: List[Task] = []
    for missed in profile.get("weekly_missed_tasks", []):
        task_obj = task_index.get(missed.get("id"))
        if task_obj:
            missed_task_infos.append(task_obj)

    # --- 3️⃣ 清理旧字段（避免新旧结构并存导致歧义） ---
    # 旧字段：
    #   - last_task: {"id": 1, "name": "..."}
    #   - weekly_missed_tasks: [{"id": 1, "name": "..."}, ...]
    enriched_profile.pop("last_task", None)
    enriched_profile.pop("weekly_missed_tasks", None)

    # --- 4️⃣ 写入增强后的字段 ---
    enriched_profile["last_task_info"] = last_task_info
    enriched_profile["weekly_missed_task_infos"] = missed_task_infos

    return enriched_profile
