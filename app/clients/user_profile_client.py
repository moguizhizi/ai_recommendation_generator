# app/clients/user_profile_client.py
import pandas as pd
import json

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    UserTrainingColumnName,
)
from utils.dataframe_utils import ColumnAccessor, safe_get


import pandas as pd
import json
from typing import Dict, Any


def fetch_user_profile(user_id: str, patient_code: str, config: Dict[str, Any]) -> Dict:
    """
    从 patient 数据中读取用户画像
    """

    patient_path = config["task"]["user_brain_score"]

    df = pd.read_parquet(patient_path)

    with open(
        config["column_mapping"][CognitiveL1DatasetName.USER_BRAIN_SCORE.value]
    ) as f:
        COLUMN_MAPPING = json.load(f)

    cols = ColumnAccessor(COLUMN_MAPPING, UserTrainingColumnName)

    # 定位用户
    user_row = None

    if user_id:
        user_df = df[df[cols.user_id] == user_id]
        if not user_df.empty:
            user_row = user_df.iloc[0]

    if user_row is None and patient_code:
        user_df = df[df[cols.patient_code] == patient_code]
        if not user_df.empty:
            user_row = user_df.iloc[0]

    if user_row is None:
        raise ValueError("User not found in patient data")

    # 构建画像
    profile = {
        "user_id": safe_get(user_row, cols.user_id),
        "patient_code": safe_get(user_row, cols.patient_code),
        "disease_tag": safe_get(user_row, cols.disease),
        "latest_level1_scores": {
            "memory": safe_get(user_row, cols.latest_memory),
            "exec": safe_get(user_row, cols.latest_executive),
            "attention": safe_get(user_row, cols.latest_attention),
            "perception": safe_get(user_row, cols.latest_perception),
        },
        "week1_level1_scores": {
            "memory": safe_get(user_row, cols.week1_memory),
            "exec": safe_get(user_row, cols.week1_executive),
            "attention": safe_get(user_row, cols.week1_attention),
            "perception": safe_get(user_row, cols.week1_perception),
        },
        "week2_level1_scores": {
            "memory": safe_get(user_row, cols.week2_memory),
            "exec": safe_get(user_row, cols.week2_executive),
            "attention": safe_get(user_row, cols.week2_attention),
            "perception": safe_get(user_row, cols.week2_perception),
        },
        "last_day_task": safe_get(user_row, cols.last_day_task),
        "weekly_missed_tasks": safe_get(user_row, cols.last_7_days_no_task),
    }

    return profile
