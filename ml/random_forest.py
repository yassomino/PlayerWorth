"""Session 5: temporal Random Forest selection and frozen-model comparison."""

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
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

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
    dict(n_estimators=300, max_depth=depth, min_samples_leaf=leaf, max_features=features)
    for depth, leaf, features in product((4, 8, 12, None), (1, 3, 8), (1.0, "sqrt"))
)


def build_pipeline(parameters: dict) -> Pipeline:
    return Pipeline(
        [("random_forest", RandomForestRegressor(**parameters, random_state=42, n_jobs=1))]
    )


def choose_candidate(results: list[dict]) -> dict:
    """Cent-level equivalence is fixed in advance, never inferred from test results."""
    best_mae = min(row["mae"] for row in results)
    tied = [row for row in results if row["mae"] <= best_mae + 0.01]
    best_rmse = min(row["rmse"] for row in tied)
    tied = [row for row in tied if row["rmse"] <= best_rmse + 0.01]
    return min(
        tied,
        key=lambda row: (
            row["parameters"]["max_depth"] or float("inf"),
            -row["parameters"]["min_samples_leaf"],
            str(row["parameters"]["max_features"]),
        ),
    )


def select_parameters(training: pd.DataFrame) -> dict[str, Any]:
    if set(training.season) != set(TRAIN_SEASONS):
        raise ValueError("Selection requires only the four training seasons")
    fitting = training.loc[training.season.isin(TRAIN_SEASONS[:-1])]
    validation = training.loc[training.season.eq(TRAIN_SEASONS[-1])]
    results = []
    for parameters in CANDIDATES:
        pipeline = build_pipeline(parameters).fit(select_features(fitting), fitting[TARGET])
        results.append(
            {
                "parameters": parameters,
                **regression_metrics(
                    validation[TARGET], pipeline.predict(select_features(validation))
                ),
            }
        )
    selected = choose_candidate(results)
    return {
        "selected_parameters": selected["parameters"],
        "selected_validation_metrics": {key: selected[key] for key in ("mae", "rmse", "r2")},
        "criterion": "MAE then RMSE (EUR 0.01 equivalence), shallower depth, larger leaf",
        "fitting_seasons": list(TRAIN_SEASONS[:-1]),
        "validation_season": TRAIN_SEASONS[-1],
        "fitting_rows": len(fitting),
        "validation_rows": len(validation),
        "candidates": results,
    }


def feature_importance(pipeline: Pipeline) -> dict:
    if list(pipeline.feature_names_in_) != FEATURES:
        raise ValueError("Unexpected feature contract")
    values = pipeline.named_steps["random_forest"].feature_importances_
    return {
        "method": "mean decrease in impurity; not causal effects or linear coefficients",
        "feature_names": FEATURES,
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
    for name in ("linear_regression", "ridge"):
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
    if any(output_dir.glob("random_forest*")):
        raise FileExistsError("Random Forest outputs exist; use a fresh --output-dir")
    selection = select_parameters(training)
    pipeline = build_pipeline(selection["selected_parameters"])
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
    metadata = {
        "schema_version": 1,
        "model_name": "random_forest",
        "model_type": "sklearn.ensemble.RandomForestRegressor",
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
        "model_parameters": pipeline.named_steps["random_forest"].get_params(),
        "random_state": 42,
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": benchmarks["linear_regression"]["dataset"],
        "frozen_artifact_hashes": frozen,
        "comparisons": comparisons,
        "code_hashes": {
            name: hash_file(Path(__file__).with_name(name))
            for name in ("random_forest.py", "baseline.py")
        },
        "prediction_postprocessing": "none",
        "residual_convention": "actual - predicted",
        **evaluation,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_dir / "random_forest.joblib")
    predictions.to_csv(
        output_dir / "random_forest_test_predictions.csv", index=False, lineterminator="\n"
    )
    metadata["model_sha256"] = hash_file(output_dir / "random_forest.joblib")
    metadata["predictions_sha256"] = hash_file(output_dir / "random_forest_test_predictions.csv")
    entries = [entry for entry in entries if entry["model"] != "random_forest"]
    entries.append(
        {
            "model": "random_forest",
            **evaluation["metrics"],
            "dataset_sha256": digest,
            "split_strategy": "temporal",
            "training_seasons": list(TRAIN_SEASONS),
            "testing_season": TEST_SEASON,
        }
    )
    for name, payload in {
        "random_forest_metadata.json": metadata,
        "random_forest_feature_importance.json": feature_importance(pipeline),
        "random_forest_analysis.json": analysis,
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
    metadata = json.loads(model_path.with_name("random_forest_metadata.json").read_text())
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
            result = evaluate_saved(args.dataset, args.output_dir / "random_forest.joblib")
    except (ValueError, OSError) as error:
        parser.exit(2, f"Random Forest failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
