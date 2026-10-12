"""Synthetic rate experiments; source rate values are never recomputed by modeling."""

import joblib
import numpy as np
import pandas as pd
import pytest

from ml import per90_experiment as exp
from ml.baseline import TARGET, TEST_SEASON, TRAIN_SEASONS
from ml.data_pipeline.ingestion import hash_file
from ml.temporal_backtest import backtest


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
    data["goals_per_90"] = data.goals / data.minutes * 90
    data["assists_per_90"] = data.assists / data.minutes * 90
    return data


def test_input_contract_and_missing(frame):
    frame["goal_contributions_per_90"] = 999
    frame.loc[0, "minutes"] = 0
    frame.loc[0, "goals_per_90"] = 7.25
    frame.loc[1, "assists_per_90"] = np.nan
    selected = exp.inputs(frame)
    assert list(selected) == ["age", "minutes", "goals", "assists", "position", *exp.RATES]
    assert selected.loc[0, "goals_per_90"] == 7.25
    assert pd.isna(selected.loc[1, "assists_per_90"])
    model = exp.build_pipeline().fit(selected, frame[TARGET])
    assert np.isfinite(model.predict(selected)).all()
    frame.loc[2, "goals_per_90"] = np.inf
    with pytest.raises(ValueError, match="infinite"):
        exp.inputs(frame)


def test_fold_preprocessing_and_future_isolation(frame):
    frame.loc[frame.season.eq(TEST_SEASON), "position"] = "AM"
    frame.loc[0, "position"] = None
    frame.loc[1, "goals_per_90"] = np.nan
    models = []

    def factory():
        model = exp.build_pipeline()
        models.append(model)
        return model

    definitions = {
        "baseline": (exp.position.build_pipeline, exp.position.inputs, exp.position.evaluate),
        "rates": (factory, exp.inputs, exp.evaluate),
    }
    summary, predictions, metrics = backtest(frame, definitions)
    assert len(models) == 4 and len({id(m) for m in models}) == 4
    for model in models:
        encoder = (
            model.named_steps["preprocess"].named_transformers_["categorical"].named_steps["encode"]
        )
        assert "AM" not in encoder.categories_[0]
        assert "UNKNOWN" in encoder.categories_[0]
    assert len(predictions) == 80 and len(metrics) == 8
    assert np.isfinite(predictions.predicted_market_value_eur).all()
    assert summary["aggregates"]["rates"]["pooled"]["rows"] == 40
    changed = frame.copy()
    changed.loc[changed.season.eq(TEST_SEASON), "goals_per_90"] = 10000
    _, after, _ = backtest(changed, definitions)
    pd.testing.assert_frame_equal(predictions[predictions.fold < 4], after[after.fold < 4])


def test_run_repeat_reload_and_preservation(frame, tmp_path):
    dataset = tmp_path / "synthetic.csv"
    frame.to_csv(dataset, index=False)
    refs = tmp_path / "reference"
    refs.mkdir()
    marker = refs / "old.json"
    marker.write_text("{}")
    digest = hash_file(dataset)
    a = exp.run(dataset, tmp_path / "a", tmp_path / "ma", refs)
    b = exp.run(dataset, tmp_path / "b", tmp_path / "mb", refs)
    assert a["aggregates"] == b["aggregates"] and a["output_hashes"] == b["output_hashes"]
    assert hash_file(dataset) == digest and marker.read_text() == "{}"
    model = joblib.load(tmp_path / "ma/xgboost_position_per90.joblib")
    assert np.isfinite(model.predict(exp.inputs(frame))).all()
    assert set(exp.NUMERICAL) <= set(model.named_steps["preprocess"].get_feature_names_out())
    with pytest.raises(FileExistsError):
        exp.run(dataset, tmp_path / "a", tmp_path / "ma", refs)
