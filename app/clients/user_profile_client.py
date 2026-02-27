# app/clients/user_profile_client.py
import requests
from typing import Dict


def fetch_user_profile(user_id: str, patient_code: str) -> Dict:
    """
    调用用户画像 / 训练数据服务，获取用户基础信息 + 训练记录 + 任务状态
    """
    url = "http://user-profile-service/api/v1/profile"

    params = {
        "user_id": user_id,
        "patient_code": patient_code
    }

    resp = requests.get(url, params=params, timeout=3)
    resp.raise_for_status()

    data = resp.json()

    # 🔹 最后一次训练任务
    last_task = data.get("last_task", {})
    last_task_info = {
        "id": last_task.get("id"),
        "name": last_task.get("name"),
    } if last_task else None

    # 🔹 过去一周未训练任务列表
    missed_tasks = []
    for task in data.get("weekly_missed_tasks", []):
        missed_tasks.append({
            "id": task.get("id"),
            "name": task.get("name")
        })

    return {
        # --- 基础画像 ---
        "train_days": data.get("train_days", 0),
        "perception_score": data.get("perception_score", 0),
        "exec_score": data.get("exec_score", 0),
        "attention": data.get("attention_score", 0),
        "memory": data.get("memory_score", 0),
        "disease_tag": data.get("disease_tag", ""),

        # --- 行为画像 ---
        "last_task": last_task_info,          # {"id": "...", "name": "..."}
        "weekly_missed_tasks": missed_tasks  # [{"id": "...", "name": "..."}, ...]
    }