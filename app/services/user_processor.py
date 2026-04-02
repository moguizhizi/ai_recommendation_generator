# app/services/user_processor.py
import json
from numbers import Number
from typing import Any, Dict

import numpy as np
import pandas as pd

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    UserTrainingColumnName,
)
from app.core.constants import Level1BrainDomain
from app.core.errors.error_codes import ErrorCode
from app.core.errors.exceptions import BizError
from app.schemas.common import Task
from utils.dataframe_utils import ColumnAccessor, safe_get


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


def build_user_matrix(last_84_days_task, task_map: Dict[str, Task]) -> np.ndarray:
    matrix = np.zeros((4, 19), dtype=int)

    if not last_84_days_task:
        return matrix

    for item in last_84_days_task:
        if not item:
            continue

        task_id = str(item).split("_", 1)[0]
        task = task_map.get(task_id)

        if not task or not task.brain_coord:
            continue

        for l1, l2 in task.brain_coord:
            matrix[l1][l2] += 1

    return matrix


def fetch_user_profile(user_id: str, patient_code: str, config: Dict[str, Any]) -> Dict:
    """
    从 patient 数据中读取用户画像（优化版）
    """

    patient_path = config["task"]["user_brain_score"]
    df = pd.read_parquet(patient_path)

    with open(
        config["column_mapping"][CognitiveL1DatasetName.USER_BRAIN_SCORE.value]
    ) as f:
        COLUMN_MAPPING = json.load(f)

    cols = ColumnAccessor(COLUMN_MAPPING, UserTrainingColumnName)

    # ======================
    # Step 1: 分别查找
    # ======================
    user_row_by_uid = None
    user_row_by_pid = None

    if user_id:
        tmp = df[df[cols.user_id] == user_id]
        if not tmp.empty:
            user_row_by_uid = tmp.iloc[0]

    if patient_code:
        tmp = df[df[cols.patient_code] == patient_code]
        if not tmp.empty:
            user_row_by_pid = tmp.iloc[0]

    # ======================
    # Step 2: 双参数一致性校验（核心简化）
    # ======================
    if user_id and patient_code:
        if user_row_by_uid is None or user_row_by_pid is None:
            raise BizError(
                ErrorCode.USER_ID_PATIENT_CODE_MISMATCH,
                user_id=user_id,
                patient_code=patient_code,
            )

        # 是否同一人
        if safe_get(user_row_by_uid, cols.patient_code) != safe_get(user_row_by_pid, cols.patient_code):
            raise BizError(
                ErrorCode.USER_ID_PATIENT_CODE_MISMATCH,
                user_id=user_id,
                patient_code=patient_code,
            )

        user_row = user_row_by_uid

    # ======================
    # Step 3: 单参数 fallback
    # ======================
    else:
        user_row = user_row_by_uid or user_row_by_pid

        if user_row is None:
            raise BizError(
                ErrorCode.USER_NOT_FOUND,
                user_id=user_id,
                patient_code=patient_code,
            )

    # ======================
    # Step 4: 构建画像（不变）
    # ======================
    latest_level1_scores = {
        Level1BrainDomain.MEMORY.value: safe_get(user_row, cols.latest_memory),
        Level1BrainDomain.EXECUTIVE.value: safe_get(user_row, cols.latest_executive),
        Level1BrainDomain.ATTENTION.value: safe_get(user_row, cols.latest_attention),
        Level1BrainDomain.PERCEPTION.value: safe_get(user_row, cols.latest_perception),
    }

    invalid_level1_scores = {
        d: v for d, v in latest_level1_scores.items() if not isinstance(v, Number)
    }
    if invalid_level1_scores:
        raise BizError(
            ErrorCode.INVALID_LATEST_LEVEL1_SCORES,
            user_id=user_id,
            patient_code=patient_code,
            invalid_scores=invalid_level1_scores,
        )

    last_84_days_task = safe_get(user_row, cols.last_84_days_task)
    if not last_84_days_task:
        raise BizError(
            ErrorCode.NEW_USER_PLAN_NOT_AVAILABLE,
            user_id=user_id,
            patient_code=patient_code,
        )

    profile = {
        "user_id": safe_get(user_row, cols.user_id),
        "patient_code": safe_get(user_row, cols.patient_code),
        "disease_tag": safe_get(user_row, cols.disease),
        "latest_level1_scores": latest_level1_scores,
        "last_day_task": safe_get(user_row, cols.last_day_task),
        "last_84_days_task": last_84_days_task,
        "last_84_days_first_task": safe_get(user_row, cols.last_84_days_first_task),
        "weekly_missed_tasks": safe_get(user_row, cols.last_7_days_no_task),
    }

    for week in range(1, 12):
        profile[f"week{week}_level1_scores"] = _build_level1_scores(
            user_row, cols, week
        )

    return profile
