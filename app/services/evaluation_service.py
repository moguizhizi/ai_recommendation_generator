import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np

from typing import Any, Dict

from sympy import Number

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    L2_INDEX_REVERSE,
    Level1BrainDomain,
    Level2BrainDomain,
    MAX_HISTORY_WEEKS,
    UserTrainingColumnName,
)
from app.services.plan_rule_engine import build_L2_brain_ability_treemap, build_l2_distribution_from_tasks, enrich_user_profile_with_brain_distribution
from app.services.task_processor import build_task_infos, get_task_repository
from app.services.user_processor import _build_level1_scores
from configs.loader import load_config

from utils.dataframe_utils import ColumnAccessor, safe_get
from utils.logger import get_logger
from utils.metrics_utils import (
    compute_kl_from_distributions,
    compute_l1_from_distributions,
    to_l2_vector,
)

logger = get_logger(__name__)


class EvaluationService:
    ROUND_DIGITS = 3
    L2_SIZE = len(Level2BrainDomain)

    def __init__(self, config: dict | None = None):
        self.config = config or load_config()

    def evaluate_all_users(self) -> dict:
        """统计 train_eval_dataset 中两段任务列表的数量差异比。"""

        evaluation_cfg = self.config.get("recommendation_evaluation", {})
        if not evaluation_cfg.get("enabled", True):
            logger.info("[EVALUATE_ALL_USERS] recommendation_evaluation is disabled")
            return {"enabled": False}

        developer_view = evaluation_cfg.get("developer_view", True)
        filter_cfg = evaluation_cfg.get("filter", {})
        metric_names = evaluation_cfg.get("metrics", ["l1_value"])
        min_ratio = filter_cfg.get("min_ratio", 0.8)
        max_ratio = filter_cfg.get("max_ratio", 1.2)

        filtered_df = self._prepare_filtered_analysis_df(
            min_ratio=min_ratio,
            max_ratio=max_ratio,
        )

        task_repo = get_task_repository(config=self.config)
        with open(
            self.config["column_mapping"][CognitiveL1DatasetName.USER_BRAIN_SCORE.value]
        ) as f:
            column_mapping = json.load(f)

        cols = ColumnAccessor(column_mapping, UserTrainingColumnName)
        metric_results = []
        l2_distribution_diff_records = []

        for _, user_row in filtered_df.iterrows():
            user_id = str(safe_get(user_row, cols.user_id))

            try:
                profile = self._fetch_user_profile(
                    user_row,
                    config=self.config,
                )
                profile["last_84_days_task_infos"] = build_task_infos(
                    profile["last_84_days_task"],
                    task_repo,
                )
                profile = enrich_user_profile_with_brain_distribution(
                    profile,
                    profile.get("last_84_days_first_task"),
                    task_repo,
                )
                recommended_tasks, _ = build_L2_brain_ability_treemap(
                    profile,
                    profile["last_84d_latest_level1_scores"],
                    task_repo,
                    k=len(profile["last_84_days_task_infos"])
                )

                ground_truth_l2_distribution = build_l2_distribution_from_tasks(
                    profile["last_84_days_task_infos"]
                )
                pred_l2_distribution = build_l2_distribution_from_tasks(
                    recommended_tasks
                )
                user_metric_result = self._compute_recommendation_metrics(
                    metric_names,
                    ground_truth_l2_distribution,
                    pred_l2_distribution,
                )
                l2_distribution_diff_records.extend(
                    self._build_l2_distribution_diff_records(
                        ground_truth_l2_distribution,
                        pred_l2_distribution,
                    )
                )
                task_hit_result = self._compute_task_hit_metrics(
                    recommended_tasks=recommended_tasks,
                    ground_truth_tasks=profile["last_84_days_task_infos"],
                )
            except Exception:
                logger.exception(
                    "[EVALUATE_ALL_USERS] failed to compute metrics for user_id=%s",
                    user_id,
                )
                continue

            metric_results.append(
                {
                    "user_id": user_id,
                    "patient_code": profile.get("patient_code"),
                    **user_metric_result,
                    **task_hit_result,
                }
            )

        metrics_df = pd.DataFrame(metric_results)
        metrics_summary = self._build_metric_summaries(
            metrics_df,
            metric_names,
        )
        task_hit_summary = self._build_task_hit_summary(metrics_df)
        l2_distribution_diff_summary = self._build_l2_distribution_diff_summary(
            l2_distribution_diff_records
        )

        result = {
            "total_users": len(filtered_df),
            "computed_users": len(metrics_df),
            "skipped_users": len(filtered_df) - len(metrics_df),
            "min_ratio": min_ratio,
            "max_ratio": max_ratio,
            "metric_names": metric_names,
            "metrics_summary": metrics_summary,
            "task_hit_summary": task_hit_summary,
            "l2_distribution_diff_summary": l2_distribution_diff_summary,
        }
        response_result = (
            result
            if developer_view
            else self._build_external_result(result)
        )

        self._save_evaluation_result(
            result=result,
            metrics_df=metrics_df,
            output_cfg=evaluation_cfg.get("output", {}),
        )

        logger.info(
            "[EVALUATE_ALL_USERS] metrics_summary=%s computed_users=%s skipped_users=%s",
            metrics_summary,
            len(metrics_df),
            len(filtered_df) - len(metrics_df),
        )

        return response_result

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
        return round(last_84_days_task_count / last_84_days_first_task_count, EvaluationService.ROUND_DIGITS)

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
            stat: round(supported_stats[stat](series), EvaluationService.ROUND_DIGITS)
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
                    "ratio": round(count / total, EvaluationService.ROUND_DIGITS),
                }
            )

        return distribution

    @staticmethod
    def _compute_recommendation_metrics(
        metric_names: list[str],
        ground_truth_l2_distribution: list[dict],
        pred_l2_distribution: list[dict],
    ) -> dict:
        metrics = {}

        for metric_name in metric_names:
            if metric_name == "l1_value":
                metrics[metric_name] = round(
                    compute_l1_from_distributions(
                        ground_truth_l2_distribution,
                        pred_l2_distribution,
                    ),
                    EvaluationService.ROUND_DIGITS,
                )
                continue
            if metric_name == "kl_value":
                metrics[metric_name] = round(
                    compute_kl_from_distributions(
                        ground_truth_l2_distribution,
                        pred_l2_distribution,
                    ),
                    EvaluationService.ROUND_DIGITS,
                )
                continue

            raise ValueError(f"Unsupported recommendation metric: {metric_name}")

        return metrics

    def _build_metric_summaries(
        self,
        metrics_df: pd.DataFrame,
        metric_names: list[str],
    ) -> dict:
        summaries = {}
        empty_series = pd.Series(dtype=float)

        for metric_name in metric_names:
            series = metrics_df[metric_name] if metric_name in metrics_df else empty_series
            summaries[metric_name] = self._build_stats(
                series,
                ["max", "min", "mean", "var"],
            )

        return summaries

    def _build_task_hit_summary(self, metrics_df: pd.DataFrame) -> dict:
        task_hit_columns = [
            "task_hit_count",
            "recommended_task_total_count",
            "recommended_task_count",
            "ground_truth_task_total_count",
            "ground_truth_task_count",
            "task_hit_rate",
            "task_cover_rate",
        ]
        summaries = {}
        empty_series = pd.Series(dtype=float)

        for column in task_hit_columns:
            series = metrics_df[column] if column in metrics_df else empty_series
            summaries[column] = self._build_stats(
                series,
                ["max", "min", "mean", "var"],
            )

        return summaries

    @classmethod
    def _build_l2_distribution_diff_records(
        cls,
        ground_truth_l2_distribution: list[dict],
        pred_l2_distribution: list[dict],
    ) -> list[dict]:
        ground_truth_vector = to_l2_vector(
            ground_truth_l2_distribution,
            l2_size=cls.L2_SIZE,
        )
        pred_vector = to_l2_vector(
            pred_l2_distribution,
            l2_size=cls.L2_SIZE,
        )
        diff_records = []

        for l2_index in range(cls.L2_SIZE):
            diff = float(ground_truth_vector[l2_index] - pred_vector[l2_index])
            diff_records.append(
                {
                    "name": L2_INDEX_REVERSE.get(l2_index, f"unknown_{l2_index}"),
                    "diff": round(diff, cls.ROUND_DIGITS),
                    "abs_diff": round(abs(diff), cls.ROUND_DIGITS),
                }
            )

        return diff_records

    @classmethod
    def _build_l2_distribution_diff_summary(
        cls,
        l2_distribution_diff_records: list[dict],
    ) -> list[dict]:
        if not l2_distribution_diff_records:
            return [
                {
                    "name": L2_INDEX_REVERSE.get(l2_index, f"unknown_{l2_index}"),
                    "mean_diff": 0.0,
                    "mean_abs_diff": 0.0,
                }
                for l2_index in range(cls.L2_SIZE)
            ]

        diff_df = pd.DataFrame(l2_distribution_diff_records)
        grouped = (
            diff_df.groupby("name", sort=False)
            .agg(
                mean_diff=("diff", "mean"),
                mean_abs_diff=("abs_diff", "mean"),
            )
            .reset_index()
        )
        summary_by_name = {
            row["name"]: {
                "mean_diff": round(float(row["mean_diff"]), cls.ROUND_DIGITS),
                "mean_abs_diff": round(float(row["mean_abs_diff"]), cls.ROUND_DIGITS),
            }
            for _, row in grouped.iterrows()
        }

        return [
            {
                "name": L2_INDEX_REVERSE.get(l2_index, f"unknown_{l2_index}"),
                "mean_diff": summary_by_name.get(
                    L2_INDEX_REVERSE.get(l2_index, f"unknown_{l2_index}"),
                    {},
                ).get("mean_diff", 0.0),
                "mean_abs_diff": summary_by_name.get(
                    L2_INDEX_REVERSE.get(l2_index, f"unknown_{l2_index}"),
                    {},
                ).get("mean_abs_diff", 0.0),
            }
            for l2_index in range(cls.L2_SIZE)
        ]

    @staticmethod
    def _build_external_result(result: dict) -> dict:
        metric_summary = {}
        for metric_name, stats in result.get("metrics_summary", {}).items():
            metric_summary[metric_name] = {
                "mean": stats.get("mean", 0.0),
                "min": stats.get("min", 0.0),
                "max": stats.get("max", 0.0),
            }

        task_hit_summary = result.get("task_hit_summary", {})

        return {
            "total_users": result.get("total_users", 0),
            "computed_users": result.get("computed_users", 0),
            "skipped_users": result.get("skipped_users", 0),
            "metrics": metric_summary,
            "task_hit": {
                "mean_hit_count": task_hit_summary.get("task_hit_count", {}).get("mean", 0.0),
                "mean_hit_rate": task_hit_summary.get("task_hit_rate", {}).get("mean", 0.0),
                "mean_cover_rate": task_hit_summary.get("task_cover_rate", {}).get("mean", 0.0),
            },
            "l2_distribution_diff_summary": result.get("l2_distribution_diff_summary", []),
        }

    @staticmethod
    def _compute_task_hit_metrics(
        recommended_tasks: list,
        ground_truth_tasks: list,
    ) -> dict:
        pred_task_map = {
            str(task.task_id): task
            for task in recommended_tasks
            if getattr(task, "task_id", None)
        }
        gt_task_map = {
            str(task.task_id): task
            for task in ground_truth_tasks
            if getattr(task, "task_id", None)
        }

        hit_task_ids = sorted(set(pred_task_map) & set(gt_task_map))
        hit_count = len(hit_task_ids)
        recommended_total_count = len(recommended_tasks)
        recommended_count = len(pred_task_map)
        ground_truth_total_count = len(ground_truth_tasks)
        ground_truth_count = len(gt_task_map)

        return {
            "task_hit_count": hit_count,
            "recommended_task_total_count": recommended_total_count,
            "recommended_task_count": recommended_count,
            "ground_truth_task_total_count": ground_truth_total_count,
            "ground_truth_task_count": ground_truth_count,
            "task_hit_rate": round(
                hit_count / recommended_count if recommended_count else 0.0,
                EvaluationService.ROUND_DIGITS,
            ),
            "task_cover_rate": round(
                hit_count / ground_truth_count if ground_truth_count else 0.0,
                EvaluationService.ROUND_DIGITS,
            ),
            "hit_task_ids": hit_task_ids,
            "hit_task_names": [
                pred_task_map[task_id].task_name
                for task_id in hit_task_ids
                if getattr(pred_task_map[task_id], "task_name", None)
            ],
        }

    @staticmethod
    def _save_evaluation_result(
        result: dict,
        metrics_df: pd.DataFrame,
        output_cfg: dict,
    ) -> None:
        summary_file = output_cfg.get("summary_file")
        details_file = output_cfg.get("details_file")

        if summary_file:
            summary_path = Path(summary_file)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            current_result = {
                "evaluated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                **result,
            }
            history = []

            if summary_path.exists():
                with open(summary_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                if isinstance(existing_data, list):
                    history = existing_data
                elif existing_data:
                    history = [existing_data]

            history.append(current_result)
            history = history[-10:]

            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)

        if details_file:
            details_path = Path(details_file)
            details_path.parent.mkdir(parents=True, exist_ok=True)
            metrics_df.to_parquet(details_path, index=False)

    @staticmethod
    def _fetch_user_profile(user_row: pd.Series, config: Dict[str, Any]) -> Dict:
        """
        从 patient 数据中读取用户画像（优化版）
        """

        with open(
            config["column_mapping"][CognitiveL1DatasetName.USER_BRAIN_SCORE.value]
        ) as f:
            COLUMN_MAPPING = json.load(f)

        cols = ColumnAccessor(COLUMN_MAPPING, UserTrainingColumnName)

        latest_level1_scores = {
            Level1BrainDomain.MEMORY.value: safe_get(user_row, cols.latest_memory),
            Level1BrainDomain.EXECUTIVE.value: safe_get(user_row, cols.latest_executive),
            Level1BrainDomain.ATTENTION.value: safe_get(user_row, cols.latest_attention),
            Level1BrainDomain.PERCEPTION.value: safe_get(user_row, cols.latest_perception),
        }
        
        last_84_days_task = safe_get(user_row, cols.last_84_days_task)

        last_84d_latest_level1_scores = {
            Level1BrainDomain.MEMORY.value: safe_get(user_row, cols.last_84d_latest_memory),
            Level1BrainDomain.EXECUTIVE.value: safe_get(user_row, cols.last_84d_latest_executive),
            Level1BrainDomain.ATTENTION.value: safe_get(user_row, cols.last_84d_latest_attention),
            Level1BrainDomain.PERCEPTION.value: safe_get(user_row, cols.last_84d_latest_perception),
        }
        
        profile = {
            "user_id": safe_get(user_row, cols.user_id),
            "patient_code": safe_get(user_row, cols.patient_code),
            "age": safe_get(user_row, cols.age),
            "disease_tag": safe_get(user_row, cols.disease),
            "latest_level1_scores": latest_level1_scores,
            "last_84d_latest_level1_scores": last_84d_latest_level1_scores,
            "last_day_task": safe_get(user_row, cols.last_day_task),
            "last_84_days_task": last_84_days_task,
            "last_84_days_first_task": safe_get(user_row, cols.last_84_days_first_task),
            "weekly_missed_tasks": safe_get(user_row, cols.last_7_days_no_task),
        }

        for week in range(1, MAX_HISTORY_WEEKS + 1):
            profile[f"week{week}_level1_scores"] = _build_level1_scores(
                user_row, cols, week
            )

        return profile
