# app/clients/user_profile_client.py
import requests

def get_user_profile(user_id: str, patient_code: str) -> dict:
    """
    调用用户画像/训练数据服务，获取真实业务数据
    """
    url = "http://user-profile-service/api/v1/profile"

    params = {
        "user_id": user_id,
        "patient_code": patient_code
    }

    resp = requests.get(url, params=params, timeout=3)
    resp.raise_for_status()

    data = resp.json()

    return {
        "train_days": data["train_days"],
        "perception_score": data["perception_score"],
        "exec_score": data["exec_score"],
        "attention": data["attention_score"],
        "memory": data["memory_score"],
        "disease_tag": data.get("disease_tag", "")
    }