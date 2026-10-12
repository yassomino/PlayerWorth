"""Small fixtures verify chronological backtesting and independent preprocessing."""

import json

import numpy as np
import pandas as pd
import pytest

from ml import temporal_backtest as bt
from ml.baseline import TARGET, TEST_SEASON, TRAIN_SEASONS, regression_metrics
from ml.data_pipeline.ingestion import hash_file


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


def test_fold_ordering_and_coverage(frame):
    seen = []
    for fold, seasons, season, train, test in bt.expanding_folds(frame):
        assert all(int(s[:4]) < int(season[:4]) for s in seasons)
        assert season not in set(train.season)
        assert set(test.season) == {season}
        assert len(train) == fold * 10 and len(test) == 10
        seen.append(season)
    assert seen == list(bt.SEASONS[1:]) and len(set(seen)) == 4
    with pytest.raises(ValueError):
        list(bt.expanding_folds(frame[frame.season != TEST_SEASON]))


def test_fresh_preprocessing_and_metrics(frame, monkeypatch):
    frame.loc[frame.season.eq("2021/22"), "position"] = None
    frame.loc[frame.season.eq("2022/23"), "position"] = "ST"
    frame.loc[frame.season.eq("2023/24"), "position"] = "CB"
    frame.loc[frame.season.eq("2024/25"), "position"] = "GK"
    frame.loc[frame.season.eq("2025/26"), "position"] = "AM"
    original = bt.build_pipeline
    models = []

    def factory():
        model = original()
        models.append(model)
        return model

    monkeypatch.setattr(bt, "build_pipeline", factory)
    summary, predictions, metrics = bt.backtest(frame)
    assert len(models) == 4 and len({id(m) for m in models}) == 4
    expected = [
        ["UNKNOWN"],
        ["ST", "UNKNOWN"],
        ["CB", "ST", "UNKNOWN"],
        ["CB", "GK", "ST", "UNKNOWN"],
    ]
    assert [row["training_categories"] for row in summary["encoder_audit"]] == expected
    assert len(predictions) == 80 and len(metrics) == 8
    assert np.isfinite(predictions.predicted_market_value_eur).all()
    assert not predictions.duplicated(["model_name", "player_id", "test_season"]).any()
    for name in bt.MODELS:
        rows = predictions[predictions.model_name == name]
        scores = regression_metrics(rows.actual_market_value_eur, rows.predicted_market_value_eur)
        assert summary["aggregates"][name]["pooled"]["mae"] == scores["mae"]
        assert summary["aggregates"][name]["pooled"]["rmse"] == scores["rmse"]
        assert summary["aggregates"][name]["pooled"]["r2"] == scores["r2"]
        assert summary["aggregates"][name]["average_of_folds"]["mean_mae"] == pytest.approx(
            metrics[metrics.model_name == name].mae.mean()
        )
    # Changing the latest season cannot influence any earlier fold prediction.
    changed = frame.copy()
    changed.loc[changed.season.eq(TEST_SEASON), TARGET] *= 100
    _, later, _ = bt.backtest(changed)
    pd.testing.assert_frame_equal(predictions[predictions.fold < 4], later[later.fold < 4])


def test_outputs_repeatability_and_frozen_files(frame, tmp_path):
    dataset = tmp_path / "synthetic.csv"
    frame.to_csv(dataset, index=False)
    models = tmp_path / "models"
    models.mkdir()
    sentinel = models / "frozen.json"
    sentinel.write_text('{"unchanged": true}')
    before = hash_file(sentinel)
    first = bt.run(dataset, tmp_path / "first", models)
    second = bt.run(dataset, tmp_path / "second", models)
    for key in ("aggregates", "comparisons", "fold_metrics", "encoder_audit", "output_hashes"):
        assert first[key] == second[key]
    assert hash_file(sentinel) == before
    assert first["dataset_sha256"] == hash_file(dataset)
    assert (
        len(
            json.loads((tmp_path / "first/temporal_backtest_summary.json").read_text())[
                "fold_metrics"
            ]
        )
        == 8
    )
    with pytest.raises(FileExistsError):
        bt.run(dataset, tmp_path / "first", models)
    with pytest.raises(ValueError):
        bt.run(dataset, models, models)
