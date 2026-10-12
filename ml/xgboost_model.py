"""Session 6: temporal XGBoost selection and frozen-model comparison."""

import argparse
import json
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.pipeline import Pipeline
from xgboost import XGBRegressor

from .baseline import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    FEATURES,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    evaluate_pipeline,
    load_dataset,
    prediction_analysis,
    regression_metrics,
    select_features,
    temporal_split,
)
from .data_pipeline.ingestion import hash_file

CANDIDATES = tuple(
    dict(
        max_depth=depth,
        learning_rate=rate,
        min_child_weight=weight,
        subsample=sample,
        colsample_bytree=columns,
    )
    for depth, rate, (weight, sample, columns) in product(
        (2, 4, 6), (0.03, 0.05, 0.1), ((1, 1.0, 1.0), (5, 0.8, 0.8))
    )
)
MAX_ROUNDS = 800
PATIENCE = 50


def build_pipeline(parameters: dict, rounds: int, early_stopping: bool = False) -> Pipeline:
    return Pipeline(
        [
            (
                "xgboost",
                XGBRegressor(
                    **parameters,
                    n_estimators=rounds,
                    objective="reg:squarederror",
                    eval_metric="mae",
                    importance_type="gain",
                    tree_method="hist",
                    device="cpu",
                    random_state=42,
                    n_jobs=1,
                    early_stopping_rounds=PATIENCE if early_stopping else None,
                ),
            )
        ]
    )


def choose_candidate(results: list[dict]) -> dict:
    best = min(row["mae"] for row in results)
    tied = [row for row in results if row["mae"] <= best + 0.01]
    best = min(row["rmse"] for row in tied)
    tied = [row for row in tied if row["rmse"] <= best + 0.01]
    best = max(row["r2"] for row in tied)
    tied = [row for row in tied if row["r2"] >= best - 1e-12]
    return min(
        tied,
        key=lambda row: (
            row["parameters"]["max_depth"],
            row["effective_rounds"],
            -row["parameters"]["min_child_weight"],
        ),
    )


def select_parameters(training: pd.DataFrame) -> dict[str, Any]:
    if set(training.season) != set(TRAIN_SEASONS):
        raise ValueError("Selection requires only the four training seasons")
    fitting = training.loc[training.season.isin(TRAIN_SEASONS[:-1])]
    validation = training.loc[training.season.eq(TRAIN_SEASONS[-1])]
    results = []
    for parameters in CANDIDATES:
        pipeline = build_pipeline(parameters, MAX_ROUNDS, early_stopping=True)
        pipeline.fit(
            select_features(fitting),
            fitting[TARGET],
            xgboost__eval_set=[(select_features(validation), validation[TARGET])],
            xgboost__verbose=False,
        )
        model = pipeline.named_steps["xgboost"]
        results.append(
            {
                "parameters": parameters,
                "best_iteration": model.best_iteration,
                "best_validation_score": float(model.best_score),
                "effective_rounds": model.best_iteration + 1,
                "trained_rounds": model.get_booster().num_boosted_rounds(),
                **regression_metrics(
                    validation[TARGET], pipeline.predict(select_features(validation))
                ),
            }
        )
    selected = choose_candidate(results)
    return {
        "selected_parameters": selected["parameters"],
        "selected_validation_metrics": {key: selected[key] for key in ("mae", "rmse", "r2")},
        "best_iteration": selected["best_iteration"],
        "best_validation_score": selected["best_validation_score"],
        "effective_rounds": selected["effective_rounds"],
        "max_rounds": MAX_ROUNDS,
        "early_stopping_rounds": PATIENCE,
        "criterion": "MAE, RMSE (EUR 0.01 tolerance), R2 (1e-12), depth, rounds, child weight",
        "fitting_seasons": list(TRAIN_SEASONS[:-1]),
        "validation_season": TRAIN_SEASONS[-1],
        "fitting_rows": len(fitting),
        "validation_rows": len(validation),
        "candidates": results,
    }


def feature_importance(pipeline: Pipeline) -> dict:
    if list(pipeline.feature_names_in_) != FEATURES:
        raise ValueError("Unexpected feature contract")
    values = pipeline.named_steps["xgboost"].feature_importances_
    raw = pipeline.named_steps["xgboost"].get_booster().get_score(importance_type="gain")
    return {
        "method": "gain",
        "normalization": "average split gain normalized to sum one",
        "feature_names": FEATURES,
        "raw_average_gain": {name: float(raw.get(name, 0)) for name in FEATURES},
        "importances": dict(
            sorted(
                zip(FEATURES, values.tolist(), strict=True), key=lambda item: item[1], reverse=True
            )
        ),
    }


def train(dataset: Path, output_dir: Path, baseline_dir: Path = DEFAULT_OUTPUT) -> dict:
    frame = load_dataset(dataset)
    training, testing = temporal_split(frame)
    digest = hash_file(dataset)
    frozen, benchmarks = {}, {}
    metrics_source = output_dir / "model_metrics.json"
    if not metrics_source.exists():
        metrics_source = baseline_dir / "model_metrics.json"
    entries = json.loads(metrics_source.read_text(encoding="utf-8"))
    for name in ("linear_regression", "ridge", "random_forest"):
        metadata = json.loads((baseline_dir / f"{name}_metadata.json").read_text())
        if (
            metadata["dataset"]["sha256"] != digest
            or metadata["feature_names"] != FEATURES
            or metadata["target"] != TARGET
            or metadata["training_seasons"] != list(TRAIN_SEASONS)
            or metadata["testing_season"] != TEST_SEASON
            or metadata["training_rows"] != len(training)
            or metadata["testing_rows"] != len(testing)
        ):
            raise ValueError("Dataset/features/split differ from frozen benchmarks")
        for path in baseline_dir.glob(f"{name}*"):
            frozen[path.name] = hash_file(path)
        for suffix, key in (
            (".joblib", "model_sha256"),
            ("_test_predictions.csv", "predictions_sha256"),
        ):
            if frozen[f"{name}{suffix}"] != metadata[key]:
                raise ValueError("Frozen artifact hash mismatch")
        matching = [entry for entry in entries if entry["model"] == name]
        if (
            len(matching) != 1
            or matching[0]["dataset_sha256"] != digest
            or any(matching[0][key] != value for key, value in metadata["metrics"].items())
        ):
            raise ValueError("Frozen metrics mismatch")
        benchmarks[name] = metadata
    if any(output_dir.glob("xgboost*")):
        raise FileExistsError("XGBoost outputs exist; use a fresh --output-dir")
    selection = select_parameters(training)
    pipeline = build_pipeline(selection["selected_parameters"], selection["effective_rounds"])
    pipeline.fit(select_features(training), training[TARGET])
    predictions, evaluation = evaluate_pipeline(pipeline, testing, float(training[TARGET].median()))
    comparisons = {}
    for name, benchmark in benchmarks.items():
        old, new = benchmark["metrics"], evaluation["metrics"]
        comparisons[name] = {
            "mae_improvement_eur": old["mae"] - new["mae"],
            "mae_improvement_percent": 100 * (old["mae"] - new["mae"]) / old["mae"],
            "rmse_improvement_eur": old["rmse"] - new["rmse"],
            "r2_change": new["r2"] - old["r2"],
        }
    analysis = {
        **prediction_analysis(predictions),
        "worst_absolute_error_eur": float(predictions.absolute_error_eur.max()),
        "median_absolute_error_eur": float(predictions.absolute_error_eur.median()),
        "minimum_prediction_eur": float(predictions.predicted_market_value_eur.min()),
        "maximum_prediction_eur": float(predictions.predicted_market_value_eur.max()),
        "minimum_training_target_eur": float(training[TARGET].min()),
        "maximum_training_target_eur": float(training[TARGET].max()),
        "negative_prediction_count": evaluation["negative_prediction_count"],
    }
    forest_predictions = pd.read_csv(
        baseline_dir / "random_forest_test_predictions.csv", dtype={"player_id": str}
    )
    identity = ["player_id", "season", *FEATURES, "actual_market_value_eur"]
    pd.testing.assert_frame_equal(
        predictions[identity].reset_index(drop=True),
        forest_predictions[identity],
        check_dtype=False,
    )
    # Fixed identities from the earlier forest error analysis; never used for selection.
    focus = predictions.loc[
        predictions.player_id.isin(["418560", "495666", "357662", "568177", "687626"])
    ].merge(
        forest_predictions[["player_id", "predicted_market_value_eur"]].rename(
            columns={"predicted_market_value_eur": "random_forest_prediction_eur"}
        ),
        on="player_id",
        validate="one_to_one",
    )
    analysis["named_player_comparison"] = focus.to_dict("records")
    metadata = {
        "schema_version": 1,
        "model_name": "xgboost",
        "model_type": "xgboost.XGBRegressor",
        "status": "experiment_not_production",
        "feature_names": FEATURES,
        "target": TARGET,
        "target_transform": "none",
        "preprocessing": "none; invalid inputs fail validation",
        "split_strategy": "temporal",
        "training_seasons": list(TRAIN_SEASONS),
        "validation_season": TRAIN_SEASONS[-1],
        "testing_season": TEST_SEASON,
        "training_rows": len(training),
        "testing_rows": len(testing),
        "rows_dropped": 0,
        "selection": selection,
        "selected_parameters": selection["selected_parameters"],
        "model_parameters": {
            key: (None if isinstance(value, float) and np.isnan(value) else value)
            for key, value in pipeline.named_steps["xgboost"].get_params().items()
        },
        "missing_parameter_note": "JSON null represents XGBoost default NaN missing sentinel",
        "random_state": 42,
        "objective": "reg:squarederror",
        "xgboost_version": xgboost.__version__,
        "effective_rounds": selection["effective_rounds"],
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": benchmarks["linear_regression"]["dataset"],
        "frozen_artifact_hashes": frozen,
        "comparisons": comparisons,
        "code_hashes": {
            name: hash_file(Path(__file__).with_name(name))
            for name in ("xgboost_model.py", "baseline.py")
        },
        "prediction_postprocessing": "none",
        "residual_convention": "actual - predicted",
        **evaluation,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_dir / "xgboost.joblib")
    predictions.to_csv(
        output_dir / "xgboost_test_predictions.csv", index=False, lineterminator="\n"
    )
    metadata["model_sha256"] = hash_file(output_dir / "xgboost.joblib")
    metadata["predictions_sha256"] = hash_file(output_dir / "xgboost_test_predictions.csv")
    entries = [entry for entry in entries if entry["model"] != "xgboost"]
    entries.append(
        {
            "model": "xgboost",
            **evaluation["metrics"],
            "dataset_sha256": digest,
            "split_strategy": "temporal",
            "training_seasons": list(TRAIN_SEASONS),
            "testing_season": TEST_SEASON,
        }
    )
    for name, payload in {
        "xgboost_metadata.json": metadata,
        "xgboost_feature_importance.json": feature_importance(pipeline),
        "xgboost_analysis.json": analysis,
        "model_metrics.json": entries,
    }.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    if hash_file(dataset) != digest or any(
        hash_file(baseline_dir / name) != value for name, value in frozen.items()
    ):
        raise RuntimeError("Frozen inputs were changed")
    return metadata


def evaluate_saved(dataset: Path, model_path: Path) -> dict:
    metadata = json.loads(model_path.with_name("xgboost_metadata.json").read_text())
    if hash_file(dataset) != metadata["dataset"]["sha256"]:
        raise ValueError("Dataset differs from training")
    if hash_file(model_path) != metadata["model_sha256"]:
        raise ValueError("Model hash mismatch")
    _, testing = temporal_split(load_dataset(dataset))
    pipeline = joblib.load(model_path)
    feature_importance(pipeline)
    return evaluate_pipeline(pipeline, testing, metadata["median_baseline"]["training_median_eur"])[
        1
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["train", "evaluate"])
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        if args.action == "train":
            result = train(args.dataset, args.output_dir, args.baseline_dir)
            result = {key: result[key] for key in ("selection", "metrics", "comparisons")}
        else:
            result = evaluate_saved(args.dataset, args.output_dir / "xgboost.joblib")
    except (ValueError, OSError) as error:
        parser.exit(2, f"XGBoost failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
