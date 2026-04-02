import json
from pathlib import Path

import pandas as pd
import numpy as np

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    UserTrainingColumnName,
)
from configs.loader import load_config
from utils.dataframe_utils import ColumnAccessor
from utils.logger import get_logger

logger = get_logger(__name__)


class EvaluationService:
    def __init__(self, config: dict | None = None):
        self.config = config or load_config()

    def evaluate_all_users(self) -> dict:
        """统计 train_eval_dataset 中两段任务列表的数量差异比。"""

        filtered_df = self._prepare_filtered_analysis_df(
            min_ratio=0.8,
            max_ratio=1.2,
        )

        
        return filtered_df

    def evaluate_single_user(self, user_id: str) -> dict:
        """单用户评估"""
        raise NotImplementedError("evaluate_single_user is not implemented yet")

    def compute_metrics(self, history, actual, recommended) -> dict:
        """计算指标（L1 / 提升等）"""
        raise NotImplementedError("compute_metrics is not implemented yet")

    def _analyze_task_count_comparison(
        self,
        df: pd.DataFrame,
        column_mapping: dict,
        metrics_cfg: dict,
    ) -> dict:
        cols = ColumnAccessor(column_mapping, UserTrainingColumnName)
        base_column = self._resolve_column(
            cols,
            metrics_cfg["source_columns"]["base"],
        )
        compare_column = self._resolve_column(
            cols,
            metrics_cfg["source_columns"]["compare"],
        )
        output_columns = metrics_cfg["output_columns"]
        stats_to_report = metrics_cfg.get("stats", ["max", "min", "mean", "var"])
        ratio_ranges = metrics_cfg.get("ratio_ranges", [])

        df = df.copy()
        df[output_columns["base_count"]] = df[base_column].apply(self._count_tasks)
        df[output_columns["compare_count"]] = df[compare_column].apply(
            self._count_tasks
        )
        df[output_columns["diff_count"]] = (
            df[output_columns["base_count"]] - df[output_columns["compare_count"]]
        )
        df[output_columns["ratio"]] = df.apply(
            lambda row: self._compute_ratio(
                row[output_columns["base_count"]],
                row[output_columns["compare_count"]],
            ),
            axis=1,
        )

        count_diff_series = df[output_columns["diff_count"]]
        ratio_series = df[output_columns["ratio"]]

        return {
            "df": df,
            "output_columns": output_columns,
            "count_diff_stats": self._build_stats(count_diff_series, stats_to_report),
            "ratio_stats": self._build_stats(ratio_series, stats_to_report),
            "ratio_range_distribution": self._build_ratio_range_distribution(
                ratio_series,
                ratio_ranges,
            ),
        }

    def _prepare_filtered_analysis_df(
        self,
        min_ratio: float,
        max_ratio: float,
    ) -> pd.DataFrame:
        dataset_cfg = self.config["train_eval_dataset"][
            CognitiveL1DatasetName.USER_BRAIN_SCORE.value
        ]
        dataset_path = Path(dataset_cfg["dataset"])
        analyzed_dataset_path = Path(
            dataset_cfg.get("analyzed_dataset", dataset_cfg["dataset"])
        )
        metrics_cfg = dataset_cfg["analysis_metrics"]["task_count_comparison"]

        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        with open(
            self.config["column_mapping"][CognitiveL1DatasetName.USER_BRAIN_SCORE.value]
        ) as f:
            column_mapping = json.load(f)

        df = pd.read_parquet(dataset_path)
        analysis_result = self._analyze_task_count_comparison(
            df=df,
            column_mapping=column_mapping,
            metrics_cfg=metrics_cfg,
        )
        analyzed_df = analysis_result["df"]

        analyzed_dataset_path.parent.mkdir(parents=True, exist_ok=True)
        analyzed_df.to_parquet(analyzed_dataset_path, index=False)
        self._log_analysis_result(
            analyzed_dataset_path=analyzed_dataset_path,
            rows=len(analyzed_df),
            analysis_result=analysis_result,
        )

        return self._filter_ratio_range_df(
            df=analyzed_df,
            ratio_column=analysis_result["output_columns"]["ratio"],
            min_ratio=min_ratio,
            max_ratio=max_ratio,
        )

    @staticmethod
    def _log_analysis_result(
        analyzed_dataset_path: Path,
        rows: int,
        analysis_result: dict,
    ) -> None:
        logger.info(
            "[EVALUATE_ALL_USERS] dataset=%s rows=%s",
            analyzed_dataset_path,
            rows,
        )
        logger.info(
            "[EVALUATE_ALL_USERS] task_diff_count stats %s",
            analysis_result["count_diff_stats"],
        )
        logger.info(
            "[EVALUATE_ALL_USERS] task_diff_ratio stats %s",
            analysis_result["ratio_stats"],
        )
        logger.info(
            "[EVALUATE_ALL_USERS] task_diff_ratio range distribution %s",
            analysis_result["ratio_range_distribution"],
        )

    @staticmethod
    def _filter_ratio_range_df(
        df: pd.DataFrame,
        ratio_column: str,
        min_ratio: float,
        max_ratio: float,
    ) -> pd.DataFrame:
        return df[(df[ratio_column] >= min_ratio) & (df[ratio_column] <= max_ratio)].copy()

    @staticmethod
    def _count_tasks(val) -> int:
        if isinstance(val, np.ndarray):
            val = val.tolist()
        if isinstance(val, (list, tuple, set)):
            return sum(1 for item in val if item is not None and str(item).strip())
        if pd.isna(val):
            return 0
        if isinstance(val, str):
            return len([item for item in val.split(";") if item.strip()])
        return 1

    @staticmethod
    def _compute_ratio(last_84_days_task_count: int, last_84_days_first_task_count: int) -> float:
        if last_84_days_first_task_count == 0:
            return 0.0
        return round(last_84_days_task_count / last_84_days_first_task_count, 2)

    @staticmethod
    def _resolve_column(cols: ColumnAccessor, raw_column_name: str) -> str:
        enum_key = UserTrainingColumnName(raw_column_name).name.lower()
        return getattr(cols, enum_key)

    @staticmethod
    def _build_stats(series: pd.Series, stats_to_report: list[str]) -> dict:
        if series.empty:
            return {stat: 0.0 for stat in stats_to_report}

        supported_stats = {
            "max": lambda s: float(s.max()),
            "min": lambda s: float(s.min()),
            "mean": lambda s: float(s.mean()),
            "var": lambda s: float(s.var()),
        }
        return {
            stat: supported_stats[stat](series)
            for stat in stats_to_report
            if stat in supported_stats
        }

    @staticmethod
    def _build_ratio_range_distribution(
        series: pd.Series,
        ratio_ranges: list[dict],
    ) -> list[dict]:
        if series.empty or not ratio_ranges:
            return []

        total = len(series)
        distribution = []

        for range_cfg in ratio_ranges:
            label = range_cfg["label"]
            min_value = range_cfg.get("min")
            max_value = range_cfg.get("max")

            mask = pd.Series(True, index=series.index)
            if min_value is not None:
                mask &= series >= min_value
            if max_value is not None:
                mask &= series < max_value

            count = int(mask.sum())
            distribution.append(
                {
                    "label": label,
                    "min": min_value,
                    "max": max_value,
                    "count": count,
                    "ratio": round(count / total, 6),
                }
            )

        return distribution
