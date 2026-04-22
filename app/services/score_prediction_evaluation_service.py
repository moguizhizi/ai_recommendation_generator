import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from typing import Any, Dict, Iterable, List

import pandas as pd

from app.core.cognitive_l1.constants import (
    CognitiveL1DatasetName,
    MAX_HISTORY_WEEKS,
    UserTrainingColumnName,
)
from app.core.constants import Level1BrainDomain
from app.core.errors.exceptions import BizError
from app.services.plan_rule_engine import (
    build_score_prediction,
    enrich_user_profile_with_domain_histories,
)
from configs.loader import load_config
from models.model_factory import ModelManager
from utils.dataframe_utils import ColumnAccessor, safe_get
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DomainColumnSpec:
    domain: str
    column_suffix: str


DOMAIN_COLUMN_SPECS = (
    DomainColumnSpec(Level1BrainDomain.PERCEPTION.value, "perception"),
    DomainColumnSpec(Level1BrainDomain.ATTENTION.value, "attention"),
    DomainColumnSpec(Level1BrainDomain.MEMORY.value, "memory"),
    DomainColumnSpec(Level1BrainDomain.EXECUTIVE.value, "executive"),
)


class ScorePredictionEvaluationService:
    """
    离线回测分数预测准确性。

    对每个用户、每个一级脑能力构造时间序列：
    week23 -> ... -> week1 -> latest
    然后用 rolling backtest 只拿目标点之前的数据预测目标点。
    """

    ROUND_DIGITS = 4

    def __init__(
        self,
        config: Dict[str, Any] | None = None,
        model_manager: ModelManager | None = None,
    ):
        self.config = config or load_config()
        self.model_manager = model_manager
        self.user_filter_stats: Dict[str, int] = {}

    def evaluate_all_users(self) -> dict:
        eval_cfg = self.config.get("score_prediction_evaluation", {})
        if not eval_cfg.get("enabled", True):
            logger.info("[SCORE_PREDICTION_EVALUATION] disabled")
            return {"enabled": False}

        user_df = self._load_evaluation_users(eval_cfg)
        details = self._build_evaluation_details(eval_cfg, user_df)
        details_df = pd.DataFrame(details)
        summary = self._build_summary(details_df, eval_cfg)
        summary["evaluated_user_count"] = int(len(user_df))

        if bool(eval_cfg.get("developer_view", False)):
            summary["user_filter"] = self.user_filter_stats

        self._write_outputs(details_df, summary, eval_cfg)
        return summary

    def _load_evaluation_users(self, eval_cfg: Dict[str, Any]) -> pd.DataFrame:
        user_df = pd.read_parquet(self.config["task"]["user_brain_score"])
        original_count = int(len(user_df))
        cols = self._load_column_accessor()
        min_history_len = int(
            eval_cfg.get(
                "min_history_len",
                self.config.get("score_prediction", {}).get("min_history_len", 3),
            )
        )
        required_score_columns = self._get_required_score_columns(
            cols,
            min_history_len,
        )

        missing_columns = [col for col in required_score_columns if col not in user_df]
        if missing_columns:
            raise ValueError(f"Missing score columns for evaluation: {missing_columns}")

        numeric_required_scores = user_df[required_score_columns].apply(
            pd.to_numeric,
            errors="coerce",
        )
        complete_score_mask = numeric_required_scores.notna().all(axis=1)
        complete_score_count = int(complete_score_mask.sum())
        latest_gt_week12_mask = self._build_latest_gt_week12_mask(
            numeric_required_scores,
            cols,
        )
        evaluation_user_mask = complete_score_mask & latest_gt_week12_mask
        filtered_df = user_df.loc[evaluation_user_mask].copy()
        improved_score_count = int(evaluation_user_mask.sum())

        max_users = eval_cfg.get("max_users")
        if max_users is not None:
            max_users = int(max_users)
            if max_users > 0 and len(filtered_df) > max_users:
                random_state = int(eval_cfg.get("random_state", 42))
                filtered_df = filtered_df.sample(n=max_users, random_state=random_state)

        self.user_filter_stats = {
            "original_user_count": original_count,
            "complete_score_user_count": complete_score_count,
            "latest_gt_week12_user_count": improved_score_count,
            "dropped_by_missing_score_count": original_count - complete_score_count,
            "dropped_by_non_improvement_count": complete_score_count
            - improved_score_count,
            "sampled_user_count": int(len(filtered_df)),
            "requires_latest_gt_week12": True,
        }

        return filtered_df

    @staticmethod
    def _build_latest_gt_week12_mask(
        numeric_scores: pd.DataFrame,
        cols: ColumnAccessor,
    ) -> pd.Series:
        mask = pd.Series(True, index=numeric_scores.index)
        for spec in DOMAIN_COLUMN_SPECS:
            latest_col = getattr(cols, f"latest_{spec.column_suffix}")
            week12_col = getattr(cols, f"week12_{spec.column_suffix}")
            mask &= numeric_scores[latest_col] > numeric_scores[week12_col]

        return mask

    def _build_evaluation_details(
        self,
        eval_cfg: Dict[str, Any],
        user_df: pd.DataFrame,
    ) -> List[dict]:
        cols = self._load_column_accessor()

        tolerance = float(eval_cfg.get("tolerance", 5))

        details: List[dict] = []
        for _, row in user_df.iterrows():
            profile = self._build_validation_profile(row=row, cols=cols)
            actual_scores = self._build_actual_scores(row=row, cols=cols)

            if profile is None or not self._is_valid_scores(actual_scores.values()):
                continue

            try:
                profile = enrich_user_profile_with_domain_histories(
                    profile,
                    config=self.config,
                )

                score_prediction = build_score_prediction(
                    profile,
                    model_manager=self._get_model_manager(),
                    config=self.config,
                )
            except (BizError, ValueError):
                continue

            details.extend(
                self._build_prediction_validation_records(
                    profile=profile,
                    score_prediction=score_prediction,
                    actual_scores=actual_scores,
                    tolerance=tolerance,
                )
            )

        return details

    def _build_validation_profile(
        self,
        *,
        row,
        cols: ColumnAccessor,
    ) -> dict | None:
        latest_level1_scores = {
            spec.domain: self._to_float_or_none(
                safe_get(row, getattr(cols, f"week12_{spec.column_suffix}"))
            )
            for spec in DOMAIN_COLUMN_SPECS
        }

        if not self._is_valid_scores(latest_level1_scores.values()):
            return None

        profile = {
            "user_id": safe_get(row, cols.user_id),
            "patient_code": safe_get(row, cols.patient_code),
            "latest_level1_scores": {
                domain: float(value)
                for domain, value in latest_level1_scores.items()
            },
        }

        for source_week in range(13, MAX_HISTORY_WEEKS + 1):
            profile_week = source_week - 12
            profile[f"week{profile_week}_level1_scores"] = {
                spec.domain: self._to_float_or_none(
                    safe_get(
                        row,
                        getattr(cols, f"week{source_week}_{spec.column_suffix}"),
                    )
                )
                for spec in DOMAIN_COLUMN_SPECS
            }

        return profile

    def _build_actual_scores(self, row, cols: ColumnAccessor) -> Dict[str, Any]:
        return {
            spec.domain: self._to_float_or_none(
                safe_get(row, getattr(cols, f"latest_{spec.column_suffix}"))
            )
            for spec in DOMAIN_COLUMN_SPECS
        }

    def _build_prediction_validation_records(
        self,
        *,
        profile: dict,
        score_prediction,
        actual_scores: Dict[str, Any],
        tolerance: float,
    ) -> List[dict]:
        details = []
        prediction_by_domain = {
            Level1BrainDomain.ATTENTION.value: score_prediction.attention,
            Level1BrainDomain.MEMORY.value: score_prediction.memory,
            Level1BrainDomain.EXECUTIVE.value: score_prediction.executive_control,
            Level1BrainDomain.PERCEPTION.value: score_prediction.perception,
        }

        for domain, prediction in prediction_by_domain.items():
            history_values = profile["domain_histories"][domain][:-1]
            current = float(prediction.historical_score)
            actual = float(actual_scores[domain])
            predicted = int(prediction.predicted_score)
            baseline_predicted = int(prediction.baseline_predicted_score)
            error = predicted - actual
            details.append(
                {
                    "user_id": profile.get("user_id"),
                    "patient_code": profile.get("patient_code"),
                    "domain": domain,
                    "prediction_current_week": 12,
                    "actual_score_source": "latest",
                    "history_len": len(history_values),
                    "history_values": history_values,
                    "current_score": current,
                    "actual_score": actual,
                    "baseline_predicted_score": baseline_predicted,
                    "predicted_score": predicted,
                    "error": error,
                    "abs_error": abs(error),
                    "hit": abs(error) <= tolerance,
                    "actual_delta": actual - current,
                    "predicted_delta": predicted - current,
                    "direction_correct": self._direction(actual - current)
                    == self._direction(predicted - current),
                }
            )

        return details

    def _load_column_accessor(self) -> ColumnAccessor:
        mapping_path = self.config["column_mapping"][
            CognitiveL1DatasetName.USER_BRAIN_SCORE.value
        ]
        with open(mapping_path, encoding="utf-8") as f:
            column_mapping = json.load(f)

        return ColumnAccessor(column_mapping, UserTrainingColumnName)

    @staticmethod
    def _get_required_score_columns(
        cols: ColumnAccessor,
        min_history_len: int,
    ) -> List[str]:
        required_columns = [
            getattr(cols, f"latest_{spec.column_suffix}")
            for spec in DOMAIN_COLUMN_SPECS
        ]
        max_required_week = min(12 + min_history_len, MAX_HISTORY_WEEKS)
        required_columns.extend(
            getattr(cols, f"week{week}_{spec.column_suffix}")
            for week in range(12, max_required_week + 1)
            for spec in DOMAIN_COLUMN_SPECS
        )

        return required_columns

    def _load_model_manager(self) -> ModelManager:
        model_manager = ModelManager()
        model_manager.load_models(self.config)
        return model_manager

    def _get_model_manager(self) -> ModelManager:
        if self.model_manager is None:
            self.model_manager = self._load_model_manager()
        return self.model_manager

    @classmethod
    def _is_valid_scores(cls, values: Iterable[Any]) -> bool:
        return all(cls._is_valid_number(value) for value in values)

    @staticmethod
    def _is_valid_number(value: Any) -> bool:
        return ScorePredictionEvaluationService._to_float_or_none(value) is not None

    @staticmethod
    def _to_float_or_none(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric_value = pd.to_numeric(value, errors="coerce")
        except (TypeError, ValueError):
            return None
        if pd.isna(numeric_value):
            return None
        return float(numeric_value)

    @staticmethod
    def _direction(delta: float) -> int:
        if delta > 0:
            return 1
        if delta < 0:
            return -1
        return 0

    def _build_summary(self, details_df: pd.DataFrame, eval_cfg: Dict[str, Any]) -> dict:
        tolerance = float(eval_cfg.get("tolerance", 5))
        developer_view = bool(eval_cfg.get("developer_view", False))
        summary = {
            "enabled": True,
            "tolerance": tolerance,
            "prediction_current_week": 12,
            "actual_score_source": "latest",
            "max_users": eval_cfg.get("max_users"),
            "overall": self._summarize_group(
                details_df,
                developer_view=developer_view,
            ),
        }

        if developer_view and not details_df.empty:
            summary["by_domain"] = {}
            for domain, group in details_df.groupby("domain"):
                summary["by_domain"][domain] = self._summarize_group(
                    group,
                    developer_view=developer_view,
                )

        return summary

    def _summarize_group(self, df: pd.DataFrame, developer_view: bool) -> dict:
        if df.empty:
            summary = {
                "sample_count": 0,
                "mae": None,
                "hit_rate": None,
                "direction_accuracy": None,
            }
            if developer_view:
                summary["rmse"] = None
                summary["bias"] = None
            return summary

        summary = {
            "sample_count": int(len(df)),
            "mae": self._round(df["abs_error"].mean()),
            "hit_rate": self._round(df["hit"].mean()),
            "direction_accuracy": self._round(df["direction_correct"].mean()),
        }
        if developer_view:
            summary["rmse"] = self._round(sqrt((df["error"] ** 2).mean()))
            summary["bias"] = self._round(df["error"].mean())

        return summary

    def _write_outputs(
        self,
        details_df: pd.DataFrame,
        summary: dict,
        eval_cfg: Dict[str, Any],
    ) -> None:
        output_cfg = eval_cfg.get("output", {})
        summary_file = output_cfg.get("summary_file")
        details_file = output_cfg.get("details_file")

        if summary_file:
            summary_path = Path(summary_file)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            with open(summary_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

        if details_file:
            details_path = Path(details_file)
            details_path.parent.mkdir(parents=True, exist_ok=True)
            details_df.to_parquet(details_path, index=False)

    def _round(self, value: float) -> float:
        return round(float(value), self.ROUND_DIGITS)
