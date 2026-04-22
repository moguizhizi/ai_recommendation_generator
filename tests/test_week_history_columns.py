import json
from pathlib import Path

import yaml

from app.core.cognitive_l1.constants import (
    MAX_HISTORY_WEEKS,
    UserTrainingColumnName,
)
from utils.dataframe_utils import ColumnAccessor


ROOT = Path(__file__).resolve().parents[1]

WEEK_NAMES = {
    1: "一",
    2: "两",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
    10: "十",
    11: "十一",
    12: "十二",
    13: "十三",
    14: "十四",
    15: "十五",
    16: "十六",
    17: "十七",
    18: "十八",
    19: "十九",
    20: "二十",
    21: "二十一",
    22: "二十二",
    23: "二十三",
}

DOMAIN_COLUMNS = [
    ("感知觉", "perception"),
    ("注意力", "attention"),
    ("记忆力", "memory"),
    ("执行控制", "executive_function"),
]


def _expected_week_columns():
    return [
        (f"倒数{WEEK_NAMES[week]}周_{cn_name}", f"week{week}_{field_name}")
        for week in range(1, MAX_HISTORY_WEEKS + 1)
        for cn_name, field_name in DOMAIN_COLUMNS
    ]


def test_week_history_columns_are_synced_across_config_mapping_and_enum():
    with open(ROOT / "configs/config.yaml", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with open(
        ROOT / "app/core/cognitive_l1/alg_cogtrain_brainscore_task_child_column_mapping.json",
        encoding="utf-8",
    ) as f:
        mapping = json.load(f)

    configured_columns = config["columns"]["alg_cogtrain_brainscore_task_child"]
    cols = ColumnAccessor(mapping, UserTrainingColumnName)

    for raw_column, mapped_column in _expected_week_columns():
        assert raw_column in configured_columns
        assert mapping[raw_column] == mapped_column
        assert UserTrainingColumnName(raw_column).value == raw_column

    for week in range(1, MAX_HISTORY_WEEKS + 1):
        assert getattr(cols, f"week{week}_perception") == f"week{week}_perception"
        assert getattr(cols, f"week{week}_attention") == f"week{week}_attention"
        assert getattr(cols, f"week{week}_memory") == f"week{week}_memory"
        assert getattr(cols, f"week{week}_executive") == (
            f"week{week}_executive_function"
        )
