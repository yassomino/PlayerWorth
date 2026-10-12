"""Frozen-setting experiment using existing scoring-rate columns."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from . import xgboost_position as position
from .baseline import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    FEATURES,
    TARGET,
    load_dataset,
    regression_metrics,
)
from .data_pipeline.ingestion import hash_file
from .preprocessing.position import normalize_position
from .temporal_backtest import DEFAULT_EVALUATION, backtest

RATES = ["goals_per_90", "assists_per_90"]
NUMERICAL = FEATURES + RATES
NAME = "xgboost_position_per90"


def inputs(frame: pd.DataFrame) -> pd.DataFrame:
    result = position.inputs(frame)
    for name in RATES:
        result[name] = pd.to_numeric(frame[name], errors="raise")
        if np.isinf(result[name]).any() or result[name].lt(0).any():
            raise ValueError("Rates must be nonnegative or NaN, never infinite")
    return result


def build_pipeline():
    model = position.build_pipeline()
    preprocessing = model.named_steps["preprocess"]
    preprocessing.transformers = [
        (name, transformer, NUMERICAL if name == "numeric" else columns)
        for name, transformer, columns in preprocessing.transformers
    ]
    return model


def evaluate(model, testing: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    prediction = np.asarray(model.predict(inputs(testing)), dtype=float)
    scores = regression_metrics(testing[TARGET], prediction)
    result = testing[["player_id", "player_name", "season", "position"]].copy()
    result["position"] = normalize_position(result[["position"]]).position
    result["actual_market_value_eur"] = testing[TARGET]
    result["predicted_market_value_eur"] = prediction
    result["residual_eur"] = result.actual_market_value_eur - prediction
    result["absolute_error_eur"] = result.residual_eur.abs()
    return result, scores


def run(
    dataset: Path,
    output_dir: Path,
    model_dir: Path = DEFAULT_OUTPUT,
    reference_dir: Path = DEFAULT_EVALUATION,
) -> dict:
    names = [
        "per90_backtest_summary.json",
        "per90_backtest_predictions.csv",
        "per90_backtest_fold_metrics.csv",
    ]
    artifacts = [
        NAME + suffix for suffix in (".joblib", "_metadata.json", "_feature_importance.json")
    ]
    if any((output_dir / name).exists() for name in names) or any(
        (model_dir / name).exists() for name in artifacts
    ):
        raise FileExistsError("Experiment outputs exist; choose fresh output and model directories")
    frozen = {
        str(p.resolve()): hash_file(p)
        for folder in (model_dir, reference_dir)
        for p in folder.glob("*")
        if p.is_file()
    }
    digest = hash_file(dataset)
    frame = load_dataset(dataset)
    inputs(frame)  # Validate without filling missing rates or recalculating them.
    definitions = {
        "xgboost_with_position": (position.build_pipeline, position.inputs, position.evaluate),
        NAME: (build_pipeline, inputs, evaluate),
    }
    summary, predictions, metrics = backtest(frame, definitions)
    summary["rate_season_counts"] = summary.pop("position_season_counts")
    old = predictions[predictions.model_name.eq("xgboost_with_position")]
    new = predictions[predictions.model_name.eq(NAME)]
    reference = reference_dir / "temporal_backtest_predictions.csv"
    if reference.exists():
        saved = pd.read_csv(reference, dtype={"player_id": str})
        saved = saved[saved.model_name.eq("xgboost_with_position")]
        pd.testing.assert_frame_equal(
            old.reset_index(drop=True), saved.reset_index(drop=True), check_dtype=False
        )
    paired = new.merge(
        old[["player_id", "test_season", "predicted_market_value_eur", "absolute_error_eur"]],
        on=["player_id", "test_season"],
        suffixes=("", "_baseline"),
        validate="one_to_one",
    )
    paired["absolute_error_improvement_eur"] = (
        paired.absolute_error_eur_baseline - paired.absolute_error_eur
    )
    summary["largest_improvement"] = paired.nlargest(1, "absolute_error_improvement_eur").to_dict(
        "records"
    )
    summary["largest_worsening"] = paired.nsmallest(1, "absolute_error_improvement_eur").to_dict(
        "records"
    )
    summary["named_players_2025_26"] = paired[
        paired.test_season.eq("2025/26")
        & paired.player_id.isin(["418560", "495666", "357662", "687626", "568177"])
    ].to_dict("records")
    summary["pooled_by_position"] = {
        name: position.position_metrics(rows) for name, rows in (("baseline", old), ("per90", new))
    }
    training = frame[frame.season.ne("2025/26")]
    correlations = [
        ("goals", RATES[0]),
        ("assists", RATES[1]),
        ("minutes", RATES[0]),
        ("minutes", RATES[1]),
    ]
    summary["training_correlations"] = {
        f"{a}__{b}": float(training[a].corr(training[b])) for a, b in correlations
    }
    model = build_pipeline().fit(inputs(training), training[TARGET])
    importance = position.feature_importance(model)
    importance["raw_production_family"] = sum(
        importance["importances"][key] for key in ("goals", "assists")
    )
    importance["rate_production_family"] = sum(importance["importances"][key] for key in RATES)
    summary["rate_inspection"] = {
        name: {
            "dtype": str(frame[name].dtype),
            "missing": int(frame[name].isna().sum()),
            **{key: float(value) for key, value in frame[name].describe().items()},
        }
        for name in RATES
    }
    summary.update(
        dataset_sha256=digest,
        prior_artifact_hashes=frozen,
        zero_minute_rows=int(frame.minutes.eq(0).sum()),
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        code_hashes={
            name: hash_file(Path(__file__).with_name(name))
            for name in ("per90_experiment.py", "temporal_backtest.py", "xgboost_position.py")
        },
        missing_policy="Rates passed through as supplied; NaN native XGBoost; infinities rejected",
        comparison_convention="per90 minus position baseline; negative MAE is improvement",
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_dir / artifacts[0])
    predictions.to_csv(output_dir / names[1], index=False, lineterminator="\n")
    metrics.to_csv(output_dir / names[2], index=False, lineterminator="\n")
    summary["output_hashes"] = {name: hash_file(output_dir / name) for name in names[1:]}
    metadata = {
        "model_name": NAME,
        "status": "descriptive_experiment_not_promoted",
        "feature_names": [*FEATURES, "position", *RATES],
        "target": TARGET,
        "parameters": position.PARAMETERS,
        "rounds": position.ROUNDS,
        "random_state": 42,
        "training_seasons": list(position.TRAIN_SEASONS),
        "training_rows": len(training),
        "dataset_sha256": digest,
        "model_sha256": hash_file(model_dir / artifacts[0]),
        "xgboost_version": position.xgboost.__version__,
        "timestamp_utc": summary["timestamp_utc"],
    }
    for path, payload in (
        (output_dir / names[0], summary),
        (model_dir / artifacts[1], metadata),
        (model_dir / artifacts[2], importance),
    ):
        path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    if hash_file(dataset) != digest or any(hash_file(Path(p)) != val for p, val in frozen.items()):
        raise RuntimeError("Prior artifacts changed")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVALUATION)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.dataset, args.output_dir, args.model_dir)
    print(
        json.dumps(
            {key: result[key] for key in ("aggregates", "comparisons", "rate_season_counts")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
