"""Small synthetic ML tests, independent of the real modeling CSV."""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline

from ml.baseline import (
    FEATURES,
    PREDICTION_COLUMNS,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    build_pipeline,
    evaluate_pipeline,
    extract_coefficients,
    load_dataset,
    prediction_analysis,
    prediction_table,
    regression_metrics,
    select_features,
    temporal_split,
)
from ml.evaluate import evaluate_saved
from ml.train import train


@pytest.fixture
def modeling_frame() -> pd.DataFrame:
    rng = np.random.default_rng(17)
    frame = pd.DataFrame(
        {
            "player_id": [f"{i:03}" for i in range(20)],
            "player_name": [f"Synthetic Player {i}" for i in range(20)],
            "season": np.repeat([*TRAIN_SEASONS, TEST_SEASON], 4),
            "age": rng.integers(18, 35, 20),
            "minutes": rng.integers(100, 3000, 20),
            "goals": rng.integers(0, 20, 20),
            "assists": rng.integers(0, 12, 20),
            "position": "test-only",
            "goals_per_90": 999,
        }
    )
    frame[TARGET] = (
        3_000_000
        - 25_000 * frame.age
        + 1000 * frame.minutes
        + 40_000 * frame.goals
        + 75_000 * frame.assists
    )
    return frame


def test_feature_whitelist_and_order(modeling_frame: pd.DataFrame) -> None:
    features = select_features(modeling_frame[modeling_frame.columns[::-1]])
    assert features.columns.tolist() == FEATURES
    assert TARGET not in features and "player_id" not in features and "goals_per_90" not in features


def test_temporal_split(modeling_frame: pd.DataFrame) -> None:
    training, testing = temporal_split(modeling_frame.sample(frac=1, random_state=7))
    assert set(training.season) == set(TRAIN_SEASONS)
    assert set(testing.season) == {TEST_SEASON}
    assert len(training) == 16 and len(testing) == 4
    assert set(training.index).isdisjoint(testing.index)


@pytest.mark.parametrize("season", ["2026/27", "2020/21"])
def test_unexpected_seasons_fail_without_dropping(
    modeling_frame: pd.DataFrame, season: str
) -> None:
    modeling_frame.loc[0, "season"] = season
    with pytest.raises(ValueError, match="Expected seasons"):
        temporal_split(modeling_frame)


@pytest.mark.parametrize("value", [np.nan, np.inf, -1])
def test_invalid_features_fail(modeling_frame: pd.DataFrame, value: float) -> None:
    modeling_frame["minutes"] = modeling_frame["minutes"].astype(float)
    modeling_frame.loc[0, "minutes"] = value
    with pytest.raises(ValueError):
        select_features(modeling_frame)


def test_missing_feature_fails(modeling_frame: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="Missing feature columns"):
        select_features(modeling_frame.drop(columns="age"))


def test_pipeline_fit_predictions_and_coefficients(modeling_frame: pd.DataFrame) -> None:
    training, testing = temporal_split(modeling_frame)
    model = build_pipeline()
    assert isinstance(model, Pipeline)
    assert len(model.steps) == 1
    assert isinstance(model.named_steps["linear_regression"], LinearRegression)
    model.fit(select_features(training), training[TARGET])
    predictions = model.predict(select_features(testing))
    assert predictions.shape == (4,)
    assert np.isfinite(predictions).all()
    parameters = extract_coefficients(model)
    assert parameters["intercept_eur"] == pytest.approx(3_000_000)
    assert parameters["coefficients_eur_per_unit"] == pytest.approx(
        {"age": -25_000, "minutes": 1000, "goals": 40_000, "assists": 75_000}
    )


def test_metrics_known_values() -> None:
    metrics = regression_metrics([0, 2, 4], [0, 0, 4])
    assert metrics["mae"] == pytest.approx(2 / 3)
    assert metrics["rmse"] == pytest.approx(np.sqrt(4 / 3))
    assert metrics["r2"] == pytest.approx(0.5)


@pytest.mark.parametrize("actual,predicted", [([1], [2]), ([2, 2], [2, 3])])
def test_undefined_r2_explicit_null(actual: list, predicted: list) -> None:
    assert regression_metrics(actual, predicted)["r2"] is None


def test_invalid_metrics_fail() -> None:
    for actual, predicted in [([], []), ([1], [1, 2]), ([1], [np.inf])]:
        with pytest.raises(ValueError):
            regression_metrics(actual, predicted)


def test_predictions_schema_residual_sign_and_analysis(modeling_frame: pd.DataFrame) -> None:
    training, testing = temporal_split(modeling_frame)
    model = build_pipeline().fit(select_features(training), training[TARGET])
    predictions = prediction_table(model, testing)
    assert predictions.columns.tolist() == PREDICTION_COLUMNS
    np.testing.assert_allclose(
        predictions.residual_eur,
        predictions.actual_market_value_eur - predictions.predicted_market_value_eur,
    )
    np.testing.assert_allclose(predictions.absolute_error_eur, predictions.residual_eur.abs())
    predictions["residual_eur"] = [10.0, -30.0, 50.0, -20.0]
    predictions["absolute_error_eur"] = predictions.residual_eur.abs()
    analysis = prediction_analysis(predictions)
    assert analysis["best_predictions"][0]["absolute_error_eur"] == 10
    assert analysis["largest_underpredictions"][0]["residual_eur"] == 50
    assert analysis["largest_overpredictions"][0]["residual_eur"] == -30


def test_median_uses_training_only(modeling_frame: pd.DataFrame) -> None:
    training, testing = temporal_split(modeling_frame)
    model = build_pipeline().fit(select_features(training), training[TARGET])
    median = float(training[TARGET].median())
    testing[TARGET] = 1e12
    _, evaluation = evaluate_pipeline(model, testing, median)
    assert evaluation["median_baseline"]["training_median_eur"] == median
    assert evaluation["median_baseline"]["metrics"]["mae"] == pytest.approx(1e12 - median)


def test_training_artifacts_reload_and_reproducibility(
    tmp_path: Path, modeling_frame: pd.DataFrame
) -> None:
    dataset = tmp_path / "test.csv"
    modeling_frame.to_csv(dataset, index=False)
    first = train(dataset, tmp_path / "first")
    second = train(dataset, tmp_path / "second")
    assert first["metrics"] == second["metrics"]
    assert first["coefficients_eur_per_unit"] == second["coefficients_eur_per_unit"]
    assert first["intercept_eur"] == second["intercept_eur"]
    model = joblib.load(tmp_path / "first/linear_regression.joblib")
    _, testing = temporal_split(load_dataset(dataset))
    assert np.isfinite(model.predict(select_features(testing))).all()
    evaluated = evaluate_saved(dataset, tmp_path / "first/linear_regression.joblib")
    assert evaluated["metrics"] == first["metrics"]
    required = {
        "model_name",
        "model_type",
        "feature_names",
        "target",
        "training_seasons",
        "testing_season",
        "training_rows",
        "testing_rows",
        "metrics",
        "intercept_eur",
        "coefficients_eur_per_unit",
        "dataset",
        "training_timestamp_utc",
        "sklearn_version",
    }
    assert required <= first.keys()
    assert first["training_rows"] == 16 and first["testing_rows"] == 4
    assert len(first["dataset"]["sha256"]) == 64
    assert first["feature_names"] == FEATURES and first["target"] == TARGET
    assert first["status"] == "baseline_not_production"
    saved = pd.read_csv(tmp_path / "first/linear_regression_test_predictions.csv")
    assert saved.columns.tolist() == PREDICTION_COLUMNS
    assert len(saved) == 4
    metrics = json.loads((tmp_path / "first/model_metrics.json").read_text())
    assert [item["model"] for item in metrics] == ["linear_regression"]
    with pytest.raises(FileExistsError):
        train(dataset, tmp_path / "first")
    dataset.write_text(dataset.read_text() + "\n")
    with pytest.raises(ValueError, match="Dataset differs"):
        evaluate_saved(dataset, tmp_path / "first/linear_regression.joblib")


def test_test_targets_cannot_change_fitted_parameters(
    tmp_path: Path, modeling_frame: pd.DataFrame
) -> None:
    dataset = tmp_path / "test.csv"
    modeling_frame.to_csv(dataset, index=False)
    first = train(dataset, tmp_path / "first")
    modeling_frame.loc[modeling_frame.season.eq(TEST_SEASON), TARGET] = 1_000_000_000
    modeling_frame.to_csv(dataset, index=False)
    second = train(dataset, tmp_path / "second")
    assert first["coefficients_eur_per_unit"] == second["coefficients_eur_per_unit"]
    assert first["intercept_eur"] == second["intercept_eur"]
    assert (
        first["median_baseline"]["training_median_eur"]
        == second["median_baseline"]["training_median_eur"]
    )


@pytest.mark.parametrize("problem", ["target_missing", "duplicate"])
def test_dataset_rejects_without_silent_removal(
    tmp_path: Path, modeling_frame: pd.DataFrame, problem: str
) -> None:
    if problem == "target_missing":
        modeling_frame[TARGET] = modeling_frame[TARGET].astype(float)
        modeling_frame.loc[0, TARGET] = np.nan
    else:
        modeling_frame = pd.concat([modeling_frame, modeling_frame.iloc[:1]])
    dataset = tmp_path / "invalid.csv"
    modeling_frame.to_csv(dataset, index=False)
    with pytest.raises(ValueError):
        load_dataset(dataset)
