"""Small synthetic Ridge experiments, independent of the downloaded CSVs."""

import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

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
from ml.ridge import (
    ALPHAS,
    build_pipeline,
    evaluate_saved,
    extract_coefficients,
    select_alpha,
    train,
)
from ml.train import train as train_linear


@pytest.fixture
def frame():
    rng = np.random.default_rng(42)
    count = 50
    data = pd.DataFrame(
        {
            "player_id": [str(i) for i in range(count)],
            "player_name": [f"Synthetic {i}" for i in range(count)],
            "season": np.repeat([*TRAIN_SEASONS, TEST_SEASON], 10),
            "age": rng.integers(18, 38, count),
            "minutes": rng.integers(1, 3000, count),
            "goals": rng.integers(0, 20, count),
            "assists": rng.integers(0, 12, count),
        }
    )
    data[TARGET] = 10_000_000 - 100_000 * data.age + 4000 * data.minutes + 100_000 * data.goals
    return data


def test_pipeline_fit_and_original_equation(frame):
    training, testing = temporal_split(frame)
    pipeline = build_pipeline(10).fit(select_features(training), training[TARGET])
    assert isinstance(pipeline.named_steps["scaler"], StandardScaler)
    assert isinstance(pipeline.named_steps["ridge"], Ridge)
    np.testing.assert_allclose(pipeline.named_steps["scaler"].mean_, training[FEATURES].mean())
    predicted = pipeline.predict(select_features(testing))
    assert len(predicted) == len(testing) and np.isfinite(predicted).all()
    coefficients = extract_coefficients(pipeline)
    original = testing[FEATURES].to_numpy() @ np.array(
        list(coefficients["coefficients_eur_per_unit"].values())
    )
    np.testing.assert_allclose(predicted, original + coefficients["intercept_eur"])


def test_alpha_candidates_temporal_isolation(frame, monkeypatch):
    from ml import ridge

    training, _ = temporal_split(frame)
    seen = []
    original = ridge.build_pipeline

    def recording(alpha):
        pipeline = original(alpha)
        fit = pipeline.fit

        def checked(features, targets):
            assert set(frame.loc[features.index, "season"]) == set(TRAIN_SEASONS[:-1])
            seen.append(alpha)
            return fit(features, targets)

        pipeline.fit = checked
        return pipeline

    monkeypatch.setattr(ridge, "build_pipeline", recording)
    result = select_alpha(training)
    assert seen == list(ALPHAS)
    assert result["fitting_rows"] == 30 and result["validation_rows"] == 10
    assert (
        result["selected_alpha"] == min(result["candidates"], key=lambda row: row["mae"])["alpha"]
    )
    assert result == select_alpha(training)
    frame.loc[frame.season.eq(TEST_SEASON), TARGET] = 1e15
    changed_training, _ = temporal_split(frame)
    assert result == select_alpha(changed_training)
    with pytest.raises(ValueError, match="training seasons"):
        select_alpha(frame)


def test_artifacts_reload_frozen_baseline_and_repeatability(frame, tmp_path):
    dataset = tmp_path / "synthetic.csv"
    frame.to_csv(dataset, index=False)
    output = tmp_path / "models"
    train_linear(dataset, output)
    frozen = {p.name: hash_file(p) for p in output.glob("linear_regression*")}
    old_entry = json.loads((output / "model_metrics.json").read_text())[0]
    first = train(dataset, output, output)
    second = train(dataset, tmp_path / "repeat", output)
    for key in ("alpha_selection", "metrics", "coefficients_eur_per_unit", "intercept_eur"):
        assert first[key] == second[key]
    assert frozen == {p.name: hash_file(p) for p in output.glob("linear_regression*")}
    assert evaluate_saved(dataset, output / "ridge.joblib")["metrics"] == first["metrics"]
    loaded = joblib.load(output / "ridge.joblib")
    assert np.isfinite(loaded.predict(select_features(frame))).all()
    assert {
        "alpha_selection",
        "dataset",
        "training_rows",
        "testing_rows",
        "feature_names",
        "metrics",
        "model_sha256",
        "training_timestamp_utc",
        "sklearn_version",
        "standardized_coefficients_eur",
        "coefficients_eur_per_unit",
    } <= first.keys()
    assert first["feature_names"] == FEATURES
    predictions = pd.read_csv(output / "ridge_test_predictions.csv")
    assert predictions.columns.tolist() == PREDICTION_COLUMNS and len(predictions) == 10
    entries = json.loads((output / "model_metrics.json").read_text())
    assert [entry["model"] for entry in entries] == ["linear_regression", "ridge"]
    assert entries[0] == old_entry
    with pytest.raises(FileExistsError):
        train(dataset, output, output)
    dataset.write_text(dataset.read_text() + "\n")
    with pytest.raises(ValueError, match="Dataset differs"):
        evaluate_saved(dataset, output / "ridge.joblib")
    with pytest.raises(ValueError, match="frozen baseline"):
        train(dataset, tmp_path / "bad", output)


@pytest.mark.parametrize("alpha", [0, -1, np.inf, np.nan])
def test_invalid_alpha(alpha):
    with pytest.raises(ValueError):
        build_pipeline(alpha)
