# app/data/datasets/cognitive_l1_dataset.py

import json
from pathlib import Path
from typing import Any, Dict

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    TaskColumnName,
    UserTrainingColumnName,
)
from app.data.loader import load_parquet_as_dataframe
from app.data.preprocess import preprocess_dataframe
from utils.dataframe_utils import ColumnAccessor
from utils.logger import get_logger

logger = get_logger(__name__)


def load_and_preprocess_dataset(config: Dict[str, Any], parquet_name: str):
    """
    Load raw parquet dataset and perform preprocessing.

    This function is designed to run in a scheduled task.
    Steps:
        1. Load raw parquet dataset
        2. Load column mapping configuration
        3. Determine numeric fields according to dataset type
        4. Run dataframe preprocessing
        5. Save processed parquet dataset
    """

    logger.debug("========== Dataset Build Started ==========")

    # --------------------------------------------------
    # Step 1: Load raw dataset
    # --------------------------------------------------
    df = load_parquet_as_dataframe(
        parquet_path=config["raw_to_processed"][parquet_name]["raw"]
    )

    logger.debug(f"Raw dataset shape: {df.shape}")
    logger.debug(f"Raw dataset columns: {list(df.columns)}")

    # --------------------------------------------------
    # Step 2: Load column mapping
    # --------------------------------------------------
    logger.debug("Loading column mapping")

    with open(config["column_mapping"][parquet_name]) as f:
        COLUMN_MAPPING = json.load(f)

    logger.debug(f"Column mapping size: {len(COLUMN_MAPPING)}")

    # --------------------------------------------------
    # Step 3: Define preprocessing fields
    # --------------------------------------------------
    logger.debug("Preparing preprocessing fields")

    date_fields = None
    required_fields = None
    multi_value_fields = None
    sep = None

    # numeric fields depend on dataset type
    if parquet_name == CognitiveL1DatasetName.USER_BRAIN_SCORE:

        cols = ColumnAccessor(COLUMN_MAPPING, UserTrainingColumnName)

        numeric_fields = [
            cols.latest_perception,
            cols.latest_attention,
            cols.latest_memory,
            cols.latest_executive,
            cols.week1_perception,
            cols.week1_attention,
            cols.week1_memory,
            cols.week1_executive,
            cols.week2_perception,
            cols.week2_attention,
            cols.week2_memory,
            cols.week2_executive,
            cols.episodic_memory,
            cols.interference_control,
            cols.response_inhibition,
            cols.spatial_working_memory,
            cols.focused_attention,
            cols.processing_speed,
            cols.time_perception,
            cols.selective_attention,
            cols.spatial_perception,
            cols.cognitive_flexibility,
            cols.motor_perception,
            cols.alert_attention,
            cols.spatial_memory,
            cols.sustained_attention,
            cols.memory_span,
            cols.conflict_inhibition,
            cols.working_memory,
            cols.number_sense,
            cols.attention_control,
        ]

        multi_value_fields = [
            cols.last_day_task,
            cols.last_7_days_no_task,
        ]

        sep = ";"

    elif parquet_name == CognitiveL1DatasetName.TRAINING_TASK:

        cols = ColumnAccessor(COLUMN_MAPPING, TaskColumnName)

        numeric_fields = [
            cols.difficulty,
            cols.start_level,
            cols.level_max,
            cols.initial_difficulty,
            cols.min_duration,
            cols.max_duration,
        ]

    else:
        raise ValueError(f"Unsupported dataset: {parquet_name}")

    logger.debug(f"Date fields: {date_fields}")
    logger.debug(f"Required fields: {required_fields}")
    logger.debug(f"Numeric fields count: {len(numeric_fields)}")

    # --------------------------------------------------
    # Step 4: Run dataframe preprocessing
    # --------------------------------------------------
    logger.debug("Running dataframe preprocessing")

    df = preprocess_dataframe(
        df=df,
        column_mapping=COLUMN_MAPPING,
        date_fields=date_fields,
        required_fields=required_fields,
        numeric_fields=numeric_fields,
        multi_value_fields=multi_value_fields,
        sep=sep,
    )

    logger.debug(f"Processed dataset shape: {df.shape}")

    # --------------------------------------------------
    # Step 5: Save processed dataset
    # --------------------------------------------------
    output_path = config["raw_to_processed"][parquet_name]["processed"]

    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Saving processed dataset -> {output_path}")

    df.to_parquet(output_path)

    logger.debug("Dataset successfully saved")
    logger.debug("========== Dataset Build Finished ==========")
