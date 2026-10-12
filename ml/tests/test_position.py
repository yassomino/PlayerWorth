"""Synthetic checks for the fixed position experiment."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import OneHotEncoder

from ml import xgboost_position as experiment
from ml.baseline import (
    FEATURES,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    evaluate_pipeline,
    select_features,
    temporal_split,
)
from ml.data_pipeline.ingestion import hash_file
from ml.preprocessing.position import normalize_position
from ml.xgboost_model import build_pipeline as numeric_pipeline


@pytest.fixture
def frame():
    rng = np.random.default_rng(47)
    data = pd.DataFrame(
        {
            "player_id": [str(i) for i in range(50)],
            "player_name": [f"Synthetic {i}" for i in range(50)],
            "season": np.repeat([*TRAIN_SEASONS, TEST_SEASON], 10),
            "age": rng.integers(18, 38, 50),
            "minutes": rng.integers(1, 3000, 50),
            "goals": rng.integers(0, 20, 50),
            "assists": rng.integers(0, 10, 50),
            "position": np.tile(["ST", "CB", None, "GK", "DM"], 10),
        }
    )
    data[TARGET] = 2_000_000 + data.minutes * 1000 + data.goals * 100_000
    return data


def test_normalization():
    raw = pd.DataFrame({"position": [None, np.nan, "", "unmapped", " st ", "CB"]})
    assert normalize_position(raw).position.tolist() == ["UNKNOWN"] * 4 + ["ST", "CB"]
    assert raw.position.iloc[-2] == " st "


def test_preprocessing_unseen_and_training_only(frame):
    training, testing = temporal_split(frame)
    testing["position"] = "AM"  # Valid position present only at test time.
    model = experiment.build_pipeline().fit(experiment.inputs(training), training[TARGET])
    preprocess = model.named_steps["preprocess"]
    encoder = preprocess.named_transformers_["categorical"].named_steps["encode"]
    assert isinstance(encoder, OneHotEncoder) and encoder.handle_unknown == "ignore"
    assert "AM" not in encoder.categories_[0]
    assert "UNKNOWN" in encoder.categories_[0]
    names = preprocess.get_feature_names_out().tolist()
    assert names[:4] == FEATURES and "position_ST" in names
    transformed = preprocess.transform(experiment.inputs(testing))
    np.testing.assert_array_equal(transformed[:, :4], testing[FEATURES])
    assert not transformed[:, 4:].any()
    predicted, scores = experiment.evaluate(model, testing)
    assert (
        len(predicted) == len(testing) and np.isfinite(predicted.predicted_market_value_eur).all()
    )
    assert np.isfinite(scores["mae"])
    importance = experiment.feature_importance(model)
    assert set(importance["importances"]) == set(names)
    assert importance["position_family_importance"] == pytest.approx(
        sum(val for name, val in importance["importances"].items() if name.startswith("position_"))
    )
    assert sum(importance["importances"].values()) == pytest.approx(1)


def test_position_metrics():
    data = pd.DataFrame(
        {
            "position": ["GK"] * 5 + ["UNKNOWN"],
            "actual_market_value_eur": [10] * 6,
            "predicted_market_value_eur": [8] * 6,
            "absolute_error_eur": [2] * 6,
        }
    )
    result = {row["position"]: row for row in experiment.position_metrics(data)}
    assert result["GK"]["mae"] == 2 and result["GK"]["rmse"] == 2
    assert result["UNKNOWN"]["n"] == 1 and result["UNKNOWN"]["rmse"] is None
    assert result["ST"]["n"] == 0 and result["ST"]["mae"] is None


def test_saved_experiment_and_frozen_baseline(frame, tmp_path, monkeypatch):
    dataset = tmp_path / "fixture.csv"
    frame.to_csv(dataset, index=False)
    baseline = tmp_path / "models"
    baseline.mkdir()
    training, testing = temporal_split(frame)
    model = numeric_pipeline(experiment.PARAMETERS, experiment.ROUNDS).fit(
        select_features(training), training[TARGET]
    )
    predictions, evaluation = evaluate_pipeline(model, testing, float(training[TARGET].median()))
    joblib.dump(model, baseline / "xgboost.joblib")
    predictions.to_csv(baseline / "xgboost_test_predictions.csv", index=False)
    metadata = {
        "feature_names": FEATURES,
        "selected_parameters": experiment.PARAMETERS,
        "effective_rounds": experiment.ROUNDS,
        "dataset": {"sha256": hash_file(dataset)},
        "training_seasons": list(TRAIN_SEASONS),
        "testing_season": TEST_SEASON,
        "training_rows": len(training),
        "testing_rows": len(testing),
        "metrics": evaluation["metrics"],
        "model_sha256": hash_file(baseline / "xgboost.joblib"),
        "predictions_sha256": hash_file(baseline / "xgboost_test_predictions.csv"),
    }
    (baseline / "xgboost_metadata.json").write_text(json.dumps(metadata))
    (baseline / "model_metrics.json").write_text(
        json.dumps([{"model": "xgboost", **evaluation["metrics"]}])
    )
    before = {p.name: hash_file(p) for p in baseline.glob("xgboost*")}
    original = experiment.build_pipeline

    def recording():
        pipeline = original()
        fit = pipeline.fit

        def checked(features, targets):
            assert set(frame.loc[features.index, "season"]) == set(TRAIN_SEASONS)
            assert list(features) == experiment.INPUTS
            return fit(features, targets)

        pipeline.fit = checked
        return pipeline

    # Observe the production fit call without storing the local test wrapper in joblib.
    original_dump = joblib.dump

    def dump(model, path):
        del model.fit
        return original_dump(model, path)

    monkeypatch.setattr(experiment, "build_pipeline", recording)
    monkeypatch.setattr(joblib, "dump", dump)
    first = experiment.train(dataset, baseline, baseline)
    second = experiment.train(dataset, tmp_path / "repeat", baseline)
    assert first["metrics"] == second["metrics"]
    assert first["predictions_sha256"] == second["predictions_sha256"]
    assert all(hash_file(baseline / name) == val for name, val in before.items())
    assert (
        experiment.evaluate_saved(dataset, baseline / "xgboost_position.joblib") == first["metrics"]
    )
    entries = json.loads((baseline / "model_metrics.json").read_text())
    assert entries[0]["comparison_name"] == "xgboost_4_features"
    assert entries[1]["model"] == "xgboost_with_position"
    assert first["training_rows"] == 40 and first["testing_rows"] == 10
    loaded = joblib.load(baseline / "xgboost_position.joblib")
    assert loaded.named_steps["xgboost"].n_estimators == 63
    assert loaded.named_steps["xgboost"].early_stopping_rounds is None
    assert first["feature_names"] == [*FEATURES, "position"]
    with pytest.raises(FileExistsError):
        experiment.train(dataset, baseline, baseline)
