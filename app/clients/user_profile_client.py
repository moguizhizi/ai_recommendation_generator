# app/clients/user_profile_client.py
import requests
from typing import Dict


# def fetch_user_profile(user_id: str, patient_code: str) -> Dict:
#     """
#     调用用户画像 / 训练数据服务，获取：
#     - 一级脑能力分数
#     - 二级脑能力分数
#     - 行为画像（最近任务 / 漏训任务）
#     - 返回 user_id 和 patient_code
#     """
#     url = "http://user-profile-service/api/v1/profile"
#     params = {"user_id": user_id, "patient_code": patient_code}

#     resp = requests.get(url, params=params, timeout=3)
#     resp.raise_for_status()
#     data = resp.json()

#     # --- 最后一次训练任务 ---
#     last_task = data.get("last_task", {})
#     last_task_info = (
#         {"id": last_task.get("id"), "name": last_task.get("name")}
#         if last_task
#         else None
#     )

#     # --- 过去一周未训练任务 ---
#     missed_tasks = [
#         {"id": t.get("id"), "name": t.get("name")}
#         for t in data.get("weekly_missed_tasks", [])
#     ]

#     # --- 一级脑能力 ---
#     level1_scores = {
#         "memory": data.get("memory_score", 0),
#         "exec": data.get("exec_score", 0),
#         "attention": data.get("attention_score", 0),
#         "perception": data.get("perception_score", 0),
#     }

#     # --- 二级脑能力 ---
#     level2_scores = {
#         "memory": {
#             "working_memory": data.get("memory_working_score", 0),
#             "spatial_memory": data.get("memory_spatial_score", 0),
#         },
#         "exec": {
#             "conflict_inhibition": data.get("exec_conflict_score", 0),
#             "interference_control": data.get("exec_interfere_score", 0),
#         },
#         "attention": {
#             "alerting": data.get("attention_alert_score", 0),
#             "sustained": data.get("attention_sustain_score", 0),
#         },
#         "perception": {"spatial_perception": data.get("perception_spatial_score", 0)},
#     }

#     return {
#         # --- 基础信息 ---
#         "user_id": user_id,
#         "patient_code": patient_code,
#         "train_days": data.get("train_days", 0),
#         "disease_tag": data.get("disease_tag", ""),
#         # --- 能力画像 ---
#         "level1_scores": level1_scores,
#         "level2_scores": level2_scores,
#         # --- 行为画像 ---
#         "last_task": last_task_info,
#         "weekly_missed_tasks": missed_tasks,
#     }


def fetch_user_profile(user_id: str, patient_code: str) -> Dict:
    """
    Mock 用户画像数据（用于本地调试）
    """

    return {
        # --- 基础画像 ---
        "user_id": user_id,
        "patient_code": patient_code,
        "train_days": 28,
        "disease_tag": "mild_cognitive_impairment",
        # --- 一级脑能力 ---
        "level1_scores": {
            "memory": 62,
            "exec": 55,
            "attention": 70,
            "perception": 68,
        },
        # --- 二级脑能力 ---
        "level2_scores": {
            "memory": {
                "working_memory": 58,
                "spatial_memory": 65,
            },
            "exec": {
                "conflict_inhibition": 50,
                "interference_control": 60,
            },
            "attention": {
                "alerting": 72,
                "sustained": 66,
            },
            "perception": {
                "spatial_perception": 69,
            },
        },
        # --- 行为画像 ---
        "last_task": {
            "id": "task_101",
            "name": "数字记忆挑战",
        },
        "weekly_missed_tasks": [
            {"id": "task_205", "name": "空间旋转训练"},
            {"id": "task_310", "name": "冲突抑制训练"},
        ],
    }
