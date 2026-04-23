#!/usr/bin/env python
"""Compare lightweight score-prediction calibration strategies.

The script reads the offline score prediction evaluation details parquet and
reports MAE/bias for post-processing strategies that only use online-available
features: domain, current_score, and predicted_delta.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_DETAILS_PATH = Path(
    "data/internal/processed/cognitive_l1/score_prediction_evaluation_details.parquet"
)
CURRENT_BINS = (0, 80, 100, 120, 140, 160, 999)
MULTIPLIER_GRID = np.round(np.arange(0.4, 2.205, 0.005), 3)


@dataclass(frozen=True)
class Metrics:
    name: str
    mae: float
    bias: float
    hit_rate: float


def round_score(values: np.ndarray) -> np.ndarray:
    return np.rint(values).clip(0, 160)


def summarize(name: str, actual: np.ndarray, predicted: np.ndarray) -> Metrics:
    error = predicted - actual
    return Metrics(
        name=name,
        mae=float(np.abs(error).mean()),
        bias=float(error.mean()),
        hit_rate=float((np.abs(error) <= 5).mean()),
    )


def format_metrics(metrics: list[Metrics]) -> str:
    rows = [
        f"{'strategy':32s} {'mae':>8s} {'bias':>8s} {'hit_rate':>9s}",
        "-" * 61,
    ]
    for item in sorted(metrics, key=lambda metric: metric.mae):
        rows.append(
            f"{item.name:32s} {item.mae:8.4f} {item.bias:8.4f} {item.hit_rate:9.4f}"
        )
    return "\n".join(rows)


def optimize_multiplier(
    current: np.ndarray,
    predicted_delta: np.ndarray,
    actual: np.ndarray,
) -> tuple[float, np.ndarray]:
    best_multiplier = 1.0
    best_predicted = round_score(current + predicted_delta)
    best_mae = np.abs(best_predicted - actual).mean()

    for multiplier in MULTIPLIER_GRID:
        predicted = round_score(current + multiplier * predicted_delta)
        mae = np.abs(predicted - actual).mean()
        if mae < best_mae:
            best_mae = mae
            best_multiplier = float(multiplier)
            best_predicted = predicted

    return best_multiplier, best_predicted


def apply_group_multipliers(
    df: pd.DataFrame,
    group_cols: list[str],
) -> tuple[dict[tuple, float], np.ndarray]:
    predicted = np.zeros(len(df), dtype=float)
    multipliers: dict[tuple, float] = {}

    for group_key, group in df.groupby(group_cols, observed=True):
        if not isinstance(group_key, tuple):
            group_key = (group_key,)
        multiplier, group_predicted = optimize_multiplier(
            group["current_score"].to_numpy(dtype=float),
            group["predicted_delta"].to_numpy(dtype=float),
            group["actual_score"].to_numpy(dtype=float),
        )
        multipliers[group_key] = multiplier
        predicted[group.index.to_numpy()] = group_predicted

    return multipliers, predicted


def fit_ridge(
    feature_df: pd.DataFrame,
    y: np.ndarray,
    alpha: float,
) -> tuple[pd.Series, float, np.ndarray]:
    x = np.column_stack([np.ones(len(feature_df)), feature_df.to_numpy(dtype=float)])
    penalty = np.eye(x.shape[1]) * alpha
    penalty[0, 0] = 0.0
    coef = np.linalg.solve(x.T @ x + penalty, x.T @ y)
    predicted = round_score(x @ coef)

    coefficients = pd.Series(coef[1:], index=feature_df.columns)
    intercept = float(coef[0])
    return coefficients, intercept, predicted


def fit_linear_calibrator(df: pd.DataFrame) -> tuple[pd.Series, float, np.ndarray]:
    feature_df = pd.get_dummies(df["domain"], prefix="domain", dtype=float)
    feature_df["current_score"] = df["current_score"].astype(float)
    feature_df["predicted_delta"] = df["predicted_delta"].astype(float)

    y = df["actual_score"].to_numpy(dtype=float)
    return fit_ridge(feature_df, y, alpha=100)


def fit_quadratic_calibrator(df: pd.DataFrame) -> tuple[pd.Series, float, np.ndarray]:
    feature_df = pd.get_dummies(df["domain"], prefix="domain", dtype=float)
    current = df["current_score"].astype(float)
    predicted_delta = df["predicted_delta"].astype(float)
    feature_df["current_score"] = current
    feature_df["predicted_delta"] = predicted_delta
    feature_df["current_score_squared"] = (current / 100) ** 2
    feature_df["predicted_delta_squared"] = (predicted_delta / 20) ** 2
    feature_df["current_delta_interaction"] = (
        (current / 100) * (predicted_delta / 20)
    )

    y = df["actual_score"].to_numpy(dtype=float)
    return fit_ridge(feature_df, y, alpha=1)


def build_metrics(df: pd.DataFrame) -> tuple[list[Metrics], dict[str, object]]:
    actual = df["actual_score"].to_numpy(dtype=float)
    baseline_predicted = df["predicted_score"].to_numpy(dtype=float)
    current = df["current_score"].to_numpy(dtype=float)
    predicted_delta = df["predicted_delta"].to_numpy(dtype=float)

    metrics = [summarize("current", actual, baseline_predicted)]
    details: dict[str, object] = {}

    multiplier, predicted = optimize_multiplier(current, predicted_delta, actual)
    metrics.append(summarize("global_delta_multiplier", actual, predicted))
    details["global_delta_multiplier"] = multiplier

    domain_multipliers, predicted = apply_group_multipliers(df, ["domain"])
    metrics.append(summarize("domain_delta_multiplier", actual, predicted))
    details["domain_delta_multiplier"] = domain_multipliers

    working_df = df.copy()
    working_df["current_bin"] = pd.cut(
        working_df["current_score"],
        bins=CURRENT_BINS,
        right=False,
    )
    current_bin_multipliers, predicted = apply_group_multipliers(
        working_df,
        ["current_bin"],
    )
    metrics.append(summarize("current_bin_delta_multiplier", actual, predicted))
    details["current_bin_delta_multiplier"] = current_bin_multipliers

    domain_bin_multipliers, predicted = apply_group_multipliers(
        working_df,
        ["domain", "current_bin"],
    )
    metrics.append(summarize("domain_current_bin_multiplier", actual, predicted))
    details["domain_current_bin_multiplier"] = domain_bin_multipliers

    coefficients, intercept, predicted = fit_linear_calibrator(df)
    metrics.append(summarize("linear_domain_current_delta", actual, predicted))
    details["linear_domain_current_delta"] = {
        "intercept": intercept,
        "coefficients": coefficients.to_dict(),
    }

    coefficients, intercept, predicted = fit_quadratic_calibrator(df)
    metrics.append(summarize("quadratic_domain_current_delta", actual, predicted))
    details["quadratic_domain_current_delta"] = {
        "intercept": intercept,
        "coefficients": coefficients.to_dict(),
    }

    return metrics, details


def print_details(details: dict[str, object]) -> None:
    print("\nBest multipliers / coefficients")
    print("-" * 61)
    for name, value in details.items():
        print(f"{name}:")
        if isinstance(value, dict):
            for key, item in value.items():
                print(f"  {key}: {item}")
        else:
            print(f"  {value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--details", type=Path, default=DEFAULT_DETAILS_PATH)
    parser.add_argument("--show-details", action="store_true")
    args = parser.parse_args()

    df = pd.read_parquet(args.details).reset_index(drop=True)
    metrics, details = build_metrics(df)
    print(format_metrics(metrics))

    if args.show_details:
        print_details(details)


if __name__ == "__main__":
    main()
