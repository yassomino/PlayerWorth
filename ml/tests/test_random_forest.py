"""Synthetic fixtures exercise the forest without reading the real football dataset."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.ensemble import RandomForestRegressor

from ml import random_forest as rf
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
    grid = tuple({**p, "n_estimators": 8} for p in (rf.CANDIDATES[0], rf.CANDIDATES[-1]))
    monkeypatch.setattr(rf, "CANDIDATES", grid)
    return grid


def test_full_grid_and_pipeline(frame):
    assert len(rf.CANDIDATES) == 24
    assert {p["n_estimators"] for p in rf.CANDIDATES} == {300}
    pipeline = rf.build_pipeline({**rf.CANDIDATES[0], "n_estimators": 8})
    assert list(pipeline.named_steps) == ["random_forest"]
    model = pipeline.named_steps["random_forest"]
    assert isinstance(model, RandomForestRegressor) and model.random_state == 42
    training, testing = temporal_split(frame)
    pipeline.fit(select_features(training), training[TARGET])
    predictions = pipeline.predict(select_features(testing))
    assert len(predictions) == 10 and np.isfinite(predictions).all()
    assert predictions.min() >= training[TARGET].min()
    assert predictions.max() <= training[TARGET].max()
    importance = rf.feature_importance(pipeline)
    assert importance["feature_names"] == FEATURES
    assert set(importance["importances"]) == set(FEATURES)
    assert sum(importance["importances"].values()) == pytest.approx(1)


def test_selection_excludes_test_and_validation_from_fitting(frame, small_grid, monkeypatch):
    training, _ = temporal_split(frame)
    original = rf.build_pipeline
    seen = []

    def recording(parameters):
        pipeline = original(parameters)
        fit = pipeline.fit

        def checked(features, targets):
            assert list(features) == FEATURES
            assert set(frame.loc[features.index, "season"]) == set(TRAIN_SEASONS[:-1])
            seen.append(parameters)
            return fit(features, targets)

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
    first = {"parameters": rf.CANDIDATES[0], "mae": 10, "rmse": 20}
    simpler = {"parameters": rf.CANDIDATES[4], "mae": 10.005, "rmse": 20.005}
    assert rf.choose_candidate([first, simpler]) == simpler
    better_rmse = {**first, "rmse": 19}
    assert rf.choose_candidate([simpler, better_rmse]) == better_rmse
    better_mae = {**first, "mae": 9, "rmse": 100}
    assert rf.choose_candidate([better_rmse, better_mae]) == better_mae


def test_artifacts_repeatability_reload_and_frozen_models(frame, small_grid, tmp_path):
    dataset = tmp_path / "synthetic.csv"
    frame.to_csv(dataset, index=False)
    output = tmp_path / "models"
    train_linear(dataset, output)
    train_ridge(dataset, output, output)
    frozen = {p.name: hash_file(p) for p in output.iterdir() if p.name != "model_metrics.json"}
    old_entries = json.loads((output / "model_metrics.json").read_text())
    first = rf.train(dataset, output, output)
    second = rf.train(dataset, tmp_path / "repeat", output)
    for key in ("selection", "metrics", "predictions_sha256"):
        assert first[key] == second[key]
    first_model = joblib.load(output / "random_forest.joblib")
    second_model = joblib.load(tmp_path / "repeat/random_forest.joblib")
    np.testing.assert_array_equal(
        first_model.predict(select_features(frame)), second_model.predict(select_features(frame))
    )
    assert all(hash_file(output / name) == digest for name, digest in frozen.items())
    assert (
        rf.evaluate_saved(dataset, output / "random_forest.joblib")["metrics"] == first["metrics"]
    )
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
        "training_timestamp_utc",
    } <= first.keys()
    predictions = pd.read_csv(output / "random_forest_test_predictions.csv")
    assert predictions.columns.tolist() == PREDICTION_COLUMNS and len(predictions) == 10
    importance = json.loads((output / "random_forest_feature_importance.json").read_text())
    assert set(importance["importances"]) == set(FEATURES)
    entries = json.loads((output / "model_metrics.json").read_text())
    assert entries[:2] == old_entries
    assert [entry["model"] for entry in entries] == ["linear_regression", "ridge", "random_forest"]
    with pytest.raises(FileExistsError):
        rf.train(dataset, output, output)
    dataset.write_text(dataset.read_text() + "\n")
    with pytest.raises(ValueError, match="Dataset differs"):
        rf.evaluate_saved(dataset, output / "random_forest.joblib")
    with pytest.raises(ValueError, match="frozen benchmarks"):
        rf.train(dataset, tmp_path / "invalid", output)
