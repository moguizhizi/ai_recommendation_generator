# app/services/user_processor.py
import pandas as pd
import json

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    UserTrainingColumnName,
)
from app.core.constants import Level1BrainDomain
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import BizError
from utils.dataframe_utils import ColumnAccessor, safe_get


import pandas as pd
import json
from typing import Dict, Any


def _build_level1_scores(user_row, cols: ColumnAccessor, week: int) -> Dict[str, Any]:
    return {
        Level1BrainDomain.MEMORY.value: safe_get(
            user_row, getattr(cols, f"week{week}_memory")
        ),
        Level1BrainDomain.EXECUTIVE.value: safe_get(
            user_row, getattr(cols, f"week{week}_executive")
        ),
        Level1BrainDomain.ATTENTION.value: safe_get(
            user_row, getattr(cols, f"week{week}_attention")
        ),
        Level1BrainDomain.PERCEPTION.value: safe_get(
            user_row, getattr(cols, f"week{week}_perception")
        ),
    }


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
        raise BizError(
            ErrorCode.USER_NOT_FOUND,
            user_id=user_id,
            patient_code=patient_code,
        )

    # 构建画像
    profile = {
        "user_id": safe_get(user_row, cols.user_id),
        "patient_code": safe_get(user_row, cols.patient_code),
        "disease_tag": safe_get(user_row, cols.disease),
        "latest_level1_scores": {
            Level1BrainDomain.MEMORY.value: safe_get(user_row, cols.latest_memory),
            Level1BrainDomain.EXECUTIVE.value: safe_get(
                user_row, cols.latest_executive
            ),
            Level1BrainDomain.ATTENTION.value: safe_get(
                user_row, cols.latest_attention
            ),
            Level1BrainDomain.PERCEPTION.value: safe_get(
                user_row, cols.latest_perception
            ),
        },
        "last_day_task": safe_get(user_row, cols.last_day_task),
        "last_84_days_task": safe_get(user_row, cols.last_84_days_task),
        "weekly_missed_tasks": safe_get(user_row, cols.last_7_days_no_task),
    }

    for week in range(1, 12):
        profile[f"week{week}_level1_scores"] = _build_level1_scores(
            user_row, cols, week
        )

    return profile
