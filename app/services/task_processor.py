# app/services/task_processor.py
from typing import Dict, List


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
    grouped = {
        "perception": [],
        "exec": [],
        "attention": [],
        "memory": []
    }

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
                "ability": raw_task.get("ability"),
            }

    # --- 4️⃣ 处理 weekly_missed_tasks ---
    missed_task_infos: List[Dict] = []

    for missed in profile.get("weekly_missed_tasks", []):
        task_id = missed.get("id")
        raw_task = task_index.get(task_id)

        if not raw_task:
            continue

        missed_task_infos.append({
            "id": task_id,
            "name": raw_task.get("name"),
            "difficulty": raw_task.get("difficulty"),
            "life_desc": raw_task.get("life_desc"),            # 生活场景描述
            "duration_min": raw_task.get("duration_min"),      # 建议训练时长（分钟）
            "ability": raw_task.get("ability"),                # perception / exec / attention / memory
            "primary_brain_ability": raw_task.get("primary_brain_ability"),     # 一级脑能力
            "secondary_brain_ability": raw_task.get("secondary_brain_ability"), # 二级脑能力
        })

    return {
        "grouped_tasks": grouped,              
        "last_task_info": last_task_info,      
        "weekly_missed_task_infos": missed_task_infos
    }