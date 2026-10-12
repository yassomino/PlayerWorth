"""Synthetic all-season freeze and production inference contract checks."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.baseline import TARGET, TEST_SEASON, TRAIN_SEASONS
from ml.data_pipeline.ingestion import hash_file
from ml.freeze_v1 import freeze
from ml.inference import load_model, predict_batch, predict_player_value, validate_inputs
from ml.temporal_backtest import run
from ml.xgboost_position import INPUTS, build_pipeline


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


@pytest.mark.parametrize(
    "key,value",
    [
        ("age", -1),
        ("minutes", np.inf),
        ("goals", np.nan),
        ("assists", 1.5),
        ("age", True),
        ("goals", "2"),
        ("position", 42),
    ],
)
def test_invalid_input(key, value):
    row = dict(age=24, minutes=3000, goals=15, assists=8, position="ST")
    row[key] = value
    with pytest.raises(ValueError):
        validate_inputs(row)


def test_contract_order_and_rejected_fields():
    row = dict(position="unseen", assists=0, goals=0, minutes=0, age=0)
    assert list(validate_inputs(row)) == INPUTS
    with pytest.raises(ValueError):
        validate_inputs({**row, "goals_per_90": 0})
    del row["minutes"]
    with pytest.raises(ValueError):
        validate_inputs(row)
    with pytest.raises(ValueError):
        validate_inputs([])
    for missing in [None, np.nan, pd.NA, ""]:
        assert (
            len(validate_inputs(dict(age=24, minutes=0, goals=0, assists=0, position=missing))) == 1
        )


def test_single_batch_and_position(frame):
    model = build_pipeline().fit(validate_inputs(frame[INPUTS]), frame[TARGET])
    rows = frame[INPUTS].iloc[:3].copy()
    rows["position"] = ["unseen", None, ""]
    batch = predict_batch(rows, model=model)
    assert np.isfinite(batch).all() and len(batch) == 3
    singles = [predict_player_value(**r, model=model) for r in rows.to_dict("records")]
    np.testing.assert_array_equal(batch, singles)
    rows["position"] = "UNKNOWN"
    np.testing.assert_array_equal(batch, predict_batch(rows, model=model))


def test_freeze_all_rows_metadata_reload_repeat(frame, tmp_path, monkeypatch):
    dataset = tmp_path / "data.csv"
    frame.to_csv(dataset, index=False)
    prior = tmp_path / "prior"
    prior.mkdir()
    marker = prior / "existing.json"
    marker.write_text("{}")
    evidence = tmp_path / "evidence"
    run(dataset, evidence, prior)
    protected = {str(p): hash_file(p) for d in [prior, evidence] for p in d.iterdir()}
    first = freeze(dataset, tmp_path / "one", evidence, prior, expected_rows=50)
    freeze(dataset, tmp_path / "two", evidence, prior, expected_rows=50)
    assert first["deployment_training_rows"] == 50
    assert first["training_seasons"] == [*TRAIN_SEASONS, TEST_SEASON]
    assert first["features"] == INPUTS and first["final_fit_test_metrics"] is None
    assert first["evaluation"]["pooled"]["rows"] == 40
    assert all(hash_file(Path(p)) == h for p, h in protected.items())
    a = load_model(tmp_path / "one/playerworth_v1.joblib")
    b = load_model(tmp_path / "two/playerworth_v1.joblib")
    np.testing.assert_array_equal(
        predict_batch(frame[INPUTS], model=a), predict_batch(frame[INPUTS], model=b)
    )
    assert (
        a.named_steps["xgboost"].get_booster().save_raw()
        == b.named_steps["xgboost"].get_booster().save_raw()
    )
    assert {
        "features",
        "dataset",
        "evaluation",
        "hyperparameters",
        "artifact_sha256",
        "known_limitations",
    } <= first.keys()
    pointer = json.loads((tmp_path / "one/current_model.json").read_text())
    assert (
        pointer["artifact"] == "playerworth_v1.joblib"
        and not Path(pointer["artifact"]).is_absolute()
    )
    from ml import inference

    monkeypatch.setattr(inference, "DEFAULT_OUTPUT", tmp_path / "one")
    assert np.isfinite(
        predict_player_value(age=24, minutes=3000, goals=15, assists=8, position="ST")
    )
    with pytest.raises(FileExistsError):
        freeze(dataset, tmp_path / "one", evidence, prior, 50)
    with pytest.raises(ValueError, match="cohort"):
        freeze(dataset, tmp_path / "bad", evidence, prior)
