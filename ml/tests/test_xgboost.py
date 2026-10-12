"""Synthetic fixtures exercise the boosting without reading the real football dataset."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

from ml import random_forest as forest
from ml import xgboost_model as rf
from ml.baseline import (
    FEATURES,
    PREDICTION_COLUMNS,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    select_features,
    temporal_split,
)
from ml.data_pipeline.ingestion import hash_file
from ml.ridge import train as train_ridge
from ml.train import train as train_linear


@pytest.fixture
def frame() -> pd.DataFrame:
    rng = np.random.default_rng(52)
    n = 50
    data = pd.DataFrame(
        {
            "player_id": [str(i) for i in range(n)],
            "player_name": [f"Synthetic {i}" for i in range(n)],
            "season": np.repeat([*TRAIN_SEASONS, TEST_SEASON], 10),
            "age": rng.integers(18, 36, n),
            "minutes": rng.integers(1, 3000, n),
            "goals": rng.integers(0, 20, n),
            "assists": rng.integers(0, 10, n),
        }
    )
    data[TARGET] = 2_000_000 + data.minutes * 1000 + data.goals**2 * 10000
    return data


@pytest.fixture
def small_grid(monkeypatch) -> tuple:
    grid = (rf.CANDIDATES[0], rf.CANDIDATES[-1])
    monkeypatch.setattr(rf, "MAX_ROUNDS", 15)
    monkeypatch.setattr(rf, "PATIENCE", 3)
    monkeypatch.setattr(rf, "CANDIDATES", grid)
    return grid


def test_full_grid_and_pipeline(frame):
    assert len(rf.CANDIDATES) == 18
    pipeline = rf.build_pipeline(rf.CANDIDATES[0], 10)
    assert list(pipeline.named_steps) == ["xgboost"]
    model = pipeline.named_steps["xgboost"]
    assert isinstance(model, XGBRegressor)
    assert model.random_state == 42 and model.objective == "reg:squarederror"
    assert model.early_stopping_rounds is None
    training, testing = temporal_split(frame)
    pipeline.fit(select_features(training), training[TARGET])
    predictions = pipeline.predict(select_features(testing))
    assert len(predictions) == 10 and np.isfinite(predictions).all()
    importance = rf.feature_importance(pipeline)
    assert importance["feature_names"] == FEATURES and importance["method"] == "gain"
    assert set(importance["importances"]) == set(FEATURES)
    assert sum(importance["importances"].values()) == pytest.approx(1)


def test_selection_excludes_test_and_validation_from_fitting(frame, small_grid, monkeypatch):
    training, _ = temporal_split(frame)
    original = rf.build_pipeline
    seen = []

    def recording(parameters, rounds, early_stopping=False):
        assert early_stopping
        pipeline = original(parameters, rounds, early_stopping)
        fit = pipeline.fit

        def checked(features, targets, **kwargs):
            validation_x, validation_y = kwargs["xgboost__eval_set"][0]
            assert set(frame.loc[validation_x.index, "season"]) == {TRAIN_SEASONS[-1]}
            assert validation_y.equals(frame.loc[validation_x.index, TARGET])
            assert list(features) == FEATURES
            assert set(frame.loc[features.index, "season"]) == set(TRAIN_SEASONS[:-1])
            seen.append(parameters)
            return fit(features, targets, **kwargs)

        pipeline.fit = checked
        return pipeline

    monkeypatch.setattr(rf, "build_pipeline", recording)
    first = rf.select_parameters(training)
    assert seen == list(small_grid)
    assert first["fitting_rows"] == 30 and first["validation_rows"] == 10
    assert len(first["candidates"]) == 2
    assert first == rf.select_parameters(training)
    frame.loc[frame.season.eq(TEST_SEASON), FEATURES + [TARGET]] = 1e10
    changed, _ = temporal_split(frame)
    assert first == rf.select_parameters(changed)
    with pytest.raises(ValueError, match="training seasons"):
        rf.select_parameters(frame)


def test_tie_breakers():
    first = {
        "parameters": rf.CANDIDATES[0],
        "mae": 10,
        "rmse": 20,
        "r2": 0.5,
        "effective_rounds": 20,
    }
    simpler = {**first, "effective_rounds": 10}
    assert rf.choose_candidate([first, simpler]) == simpler
    better_rmse = {**first, "rmse": 19}
    assert rf.choose_candidate([simpler, better_rmse]) == better_rmse
    better_mae = {**first, "mae": 9, "rmse": 100}
    assert rf.choose_candidate([better_rmse, better_mae]) == better_mae


def test_artifacts_repeatability_reload_and_frozen_models(frame, small_grid, tmp_path, monkeypatch):
    dataset = tmp_path / "synthetic.csv"
    frame.to_csv(dataset, index=False)
    output = tmp_path / "models"
    train_linear(dataset, output)
    train_ridge(dataset, output, output)
    monkeypatch.setattr(forest, "CANDIDATES", ({**forest.CANDIDATES[0], "n_estimators": 5},))
    forest.train(dataset, output, output)
    frozen = {p.name: hash_file(p) for p in output.iterdir() if p.name != "model_metrics.json"}
    old_entries = json.loads((output / "model_metrics.json").read_text())
    first = rf.train(dataset, output, output)
    second = rf.train(dataset, tmp_path / "repeat", output)
    for key in ("selection", "metrics", "predictions_sha256"):
        assert first[key] == second[key]
    first_model = joblib.load(output / "xgboost.joblib")
    estimator = first_model.named_steps["xgboost"]
    assert estimator.early_stopping_rounds is None
    assert estimator.get_booster().num_boosted_rounds() == first["effective_rounds"]
    assert first["effective_rounds"] == first["selection"]["best_iteration"] + 1
    second_model = joblib.load(tmp_path / "repeat/xgboost.joblib")
    np.testing.assert_array_equal(
        first_model.predict(select_features(frame)), second_model.predict(select_features(frame))
    )
    assert all(hash_file(output / name) == digest for name, digest in frozen.items())
    assert rf.evaluate_saved(dataset, output / "xgboost.joblib")["metrics"] == first["metrics"]
    assert {
        "model_name",
        "model_type",
        "feature_names",
        "target",
        "training_seasons",
        "validation_season",
        "testing_season",
        "training_rows",
        "testing_rows",
        "selection",
        "selected_parameters",
        "metrics",
        "dataset",
        "random_state",
        "sklearn_version",
        "xgboost_version",
        "effective_rounds",
        "objective",
        "training_timestamp_utc",
    } <= first.keys()
    predictions = pd.read_csv(output / "xgboost_test_predictions.csv")
    assert predictions.columns.tolist() == PREDICTION_COLUMNS and len(predictions) == 10
    importance = json.loads((output / "xgboost_feature_importance.json").read_text())
    assert set(importance["importances"]) == set(FEATURES)
    entries = json.loads((output / "model_metrics.json").read_text())
    assert entries[:3] == old_entries
    assert [entry["model"] for entry in entries] == [
        "linear_regression",
        "ridge",
        "random_forest",
        "xgboost",
    ]
    with pytest.raises(FileExistsError):
        rf.train(dataset, output, output)
    dataset.write_text(dataset.read_text() + "\n")
    with pytest.raises(ValueError, match="Dataset differs"):
        rf.evaluate_saved(dataset, output / "xgboost.joblib")
    with pytest.raises(ValueError, match="frozen benchmarks"):
        rf.train(dataset, tmp_path / "invalid", output)
