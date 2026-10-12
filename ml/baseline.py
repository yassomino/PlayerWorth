"""Shared validation and evaluation for the four-feature linear baseline."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.pipeline import Pipeline

FEATURES = ["age", "minutes", "goals", "assists"]
TARGET = "market_value_eur"
TRAIN_SEASONS = ("2021/22", "2022/23", "2023/24", "2024/25")
TEST_SEASON = "2025/26"
DEFAULT_DATASET = Path(__file__).parent / "data/processed/player_seasons.csv"
DEFAULT_OUTPUT = Path(__file__).parent / "models"
PREDICTION_COLUMNS = [
    "player_id",
    "player_name",
    "season",
    *FEATURES,
    "actual_market_value_eur",
    "predicted_market_value_eur",
    "residual_eur",
    "absolute_error_eur",
]


def select_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Whitelist and order inputs; never pass identifiers, target, or dates to fit."""
    missing = set(FEATURES) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing feature columns: {sorted(missing)}")
    features = frame.loc[:, FEATURES].apply(pd.to_numeric, errors="raise")
    if features.isna().any().any():
        raise ValueError(
            f"Missing feature values: {features.isna().sum().to_dict()}; no rows dropped"
        )
    if not np.isfinite(features.to_numpy(dtype=float)).all() or features.lt(0).any().any():
        raise ValueError("Features must be finite and nonnegative; no rows dropped")
    if not features["age"].between(1, 100).all():
        raise ValueError("Age must be in [1, 100]; no rows dropped")
    return features


def load_dataset(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"player_id": str, "player_name": str, "season": str})
    required = {"player_id", "player_name", "season", TARGET, *FEATURES}
    if missing := required - set(frame.columns):
        raise ValueError(f"Missing dataset columns: {sorted(missing)}")
    if frame.empty or frame[["player_id", "player_name", "season"]].isna().any().any():
        raise ValueError("Dataset must contain identified player-season rows")
    if frame.duplicated(["player_id", "season"]).any():
        raise ValueError("Duplicate player-season rows; no rows dropped")
    frame[FEATURES] = select_features(frame)
    frame[TARGET] = pd.to_numeric(frame[TARGET], errors="raise")
    if not np.isfinite(frame[TARGET]).all() or frame[TARGET].lt(0).any():
        raise ValueError("Target must be present, finite, and nonnegative; no rows dropped")
    return frame


def temporal_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The Session 3 split is fixed; refuse unrequested seasons rather than silently drop them."""
    expected = {*TRAIN_SEASONS, TEST_SEASON}
    actual = set(frame["season"])
    if actual != expected:
        raise ValueError(f"Expected seasons {sorted(expected)}, found {sorted(actual)}")
    train = frame.loc[frame["season"].isin(TRAIN_SEASONS)].copy()
    test = frame.loc[frame["season"].eq(TEST_SEASON)].copy()
    return train, test


def inspect_dataset(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "shape": list(frame.shape),
        "dtypes": frame[FEATURES + [TARGET]].dtypes.astype(str).to_dict(),
        "missing_values": frame[FEATURES + [TARGET]].isna().sum().to_dict(),
        "season_counts": frame["season"].value_counts().sort_index().to_dict(),
        "target_distribution_eur": frame[TARGET]
        .describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
        .to_dict(),
        "feature_summary": frame[FEATURES].describe().to_dict(),
        "rows_dropped": 0,
    }


def build_pipeline() -> Pipeline:
    # Current features are complete. No imputation/scaling changes their interpretable units.
    return Pipeline([("linear_regression", LinearRegression())])


def regression_metrics(actual: Any, predicted: Any) -> dict[str, float | None]:
    y, prediction = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if y.ndim != 1 or y.shape != prediction.shape or not y.size:
        raise ValueError("Metrics require equally sized nonempty one-dimensional arrays")
    if not np.isfinite(y).all() or not np.isfinite(prediction).all():
        raise ValueError("Metrics require finite values")
    # R² is undefined for a single observation or constant targets; JSON null is explicit.
    r2 = float(r2_score(y, prediction)) if len(y) >= 2 and np.ptp(y) > 0 else None
    return {
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(root_mean_squared_error(y, prediction)),
        "r2": r2,
    }


def extract_coefficients(pipeline: Pipeline) -> dict[str, Any]:
    if list(pipeline.feature_names_in_) != FEATURES:
        raise ValueError("Model feature names/order do not match the baseline contract")
    model = pipeline.named_steps["linear_regression"]
    return {
        "feature_names": FEATURES.copy(),
        "intercept_eur": float(model.intercept_),
        "coefficients_eur_per_unit": dict(zip(FEATURES, map(float, model.coef_), strict=True)),
    }


def prediction_table(pipeline: Pipeline, test: pd.DataFrame) -> pd.DataFrame:
    predictions = np.asarray(pipeline.predict(select_features(test)), dtype=float)
    if predictions.shape != (len(test),) or not np.isfinite(predictions).all():
        raise ValueError("Predictions must be finite and match the test row count")
    result = test.loc[:, ["player_id", "player_name", "season", *FEATURES]].copy()
    result["actual_market_value_eur"] = test[TARGET]
    result["predicted_market_value_eur"] = predictions
    result["residual_eur"] = result["actual_market_value_eur"] - predictions
    result["absolute_error_eur"] = result["residual_eur"].abs()
    return result[PREDICTION_COLUMNS]


def evaluate_pipeline(
    pipeline: Pipeline, test: pd.DataFrame, training_median: float
) -> tuple[pd.DataFrame, dict[str, Any]]:
    predictions = prediction_table(pipeline, test)
    comparison = regression_metrics(test[TARGET], np.full(len(test), training_median))
    return predictions, {
        "metrics": regression_metrics(test[TARGET], predictions["predicted_market_value_eur"]),
        "median_baseline": {"training_median_eur": training_median, "metrics": comparison},
        "negative_prediction_count": int(predictions["predicted_market_value_eur"].lt(0).sum()),
        "minimum_prediction_eur": float(predictions["predicted_market_value_eur"].min()),
    }


def prediction_analysis(predictions: pd.DataFrame) -> dict[str, Any]:
    stable = predictions.sort_values("player_id", kind="stable")
    columns = [
        "player_id",
        "player_name",
        "season",
        "actual_market_value_eur",
        "predicted_market_value_eur",
        "residual_eur",
        "absolute_error_eur",
    ]
    return {
        "residual_convention": "actual - predicted; positive means underprediction",
        "best_predictions": stable.sort_values("absolute_error_eur", kind="stable")
        .head(5)[columns]
        .to_dict("records"),
        "largest_underpredictions": stable.loc[stable["residual_eur"].gt(0)]
        .sort_values("residual_eur", ascending=False, kind="stable")
        .head(5)[columns]
        .to_dict("records"),
        "largest_overpredictions": stable.loc[stable["residual_eur"].lt(0)]
        .sort_values("residual_eur", kind="stable")
        .head(5)[columns]
        .to_dict("records"),
    }
