"""Session 4 Ridge experiment; reuse baseline contracts without changing its artifacts."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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

ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)


def build_pipeline(alpha: float) -> Pipeline:
    if not np.isfinite(alpha) or alpha <= 0:
        raise ValueError("Alpha must be finite and positive")
    return Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=alpha, solver="svd"))])


def select_alpha(training: pd.DataFrame) -> dict[str, Any]:
    """Accept only outer-training seasons; never accept the held-out season."""
    if set(training.season) != set(TRAIN_SEASONS):
        raise ValueError("Alpha selection requires only the four training seasons")
    fitting = training.loc[training.season.isin(TRAIN_SEASONS[:-1])]
    validation = training.loc[training.season.eq(TRAIN_SEASONS[-1])]
    results = []
    for alpha in ALPHAS:
        pipeline = build_pipeline(alpha).fit(select_features(fitting), fitting[TARGET])
        results.append(
            {
                "alpha": alpha,
                **regression_metrics(
                    validation[TARGET], pipeline.predict(select_features(validation))
                ),
            }
        )
    return {
        "selected_alpha": min(results, key=lambda row: (row["mae"], row["alpha"]))["alpha"],
        "criterion": "lowest validation MAE; lower alpha breaks exact ties",
        "fitting_seasons": list(TRAIN_SEASONS[:-1]),
        "validation_season": TRAIN_SEASONS[-1],
        "fitting_rows": len(fitting),
        "validation_rows": len(validation),
        "candidates": results,
    }


def extract_coefficients(pipeline: Pipeline) -> dict[str, Any]:
    if list(pipeline.feature_names_in_) != FEATURES:
        raise ValueError("Unexpected feature contract")
    scaler, model = pipeline.named_steps["scaler"], pipeline.named_steps["ridge"]
    original = model.coef_ / scaler.scale_
    return {
        "feature_names": FEATURES,
        "standardized_coefficients_eur": dict(zip(FEATURES, model.coef_.tolist(), strict=True)),
        "standardized_intercept_eur": float(model.intercept_),
        "coefficients_eur_per_unit": dict(zip(FEATURES, original.tolist(), strict=True)),
        "intercept_eur": float(model.intercept_ - original @ scaler.mean_),
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "conversion": (
            "beta_original = beta_scaled / scale; b_original = b_scaled - beta_original @ mean"
        ),
    }


def train(dataset: Path, output_dir: Path, baseline_dir: Path = DEFAULT_OUTPUT) -> dict:
    frame = load_dataset(dataset)
    training, testing = temporal_split(frame)
    baseline = json.loads((baseline_dir / "linear_regression_metadata.json").read_text())
    if (
        baseline["dataset"]["sha256"] != hash_file(dataset)
        or baseline["feature_names"] != FEATURES
        or baseline["training_seasons"] != list(TRAIN_SEASONS)
        or baseline["testing_season"] != TEST_SEASON
        or baseline["training_rows"] != len(training)
        or baseline["testing_rows"] != len(testing)
    ):
        raise ValueError("Dataset/features/split differ from frozen baseline")
    frozen = {path.name: hash_file(path) for path in baseline_dir.glob("linear_regression*")}
    if frozen.get("linear_regression.joblib") != baseline["model_sha256"]:
        raise ValueError("Frozen baseline model hash mismatch")
    if frozen.get("linear_regression_test_predictions.csv") != baseline["predictions_sha256"]:
        raise ValueError("Frozen baseline predictions hash mismatch")
    metrics_path = output_dir / "model_metrics.json"
    metrics_source = metrics_path if metrics_path.exists() else baseline_dir / "model_metrics.json"
    entries = json.loads(metrics_source.read_text())
    linear = [entry for entry in entries if entry["model"] == "linear_regression"]
    if len(linear) != 1 or any(
        linear[0][key] != value for key, value in baseline["metrics"].items()
    ):
        raise ValueError("Frozen metrics mismatch")
    if linear[0]["dataset_sha256"] != hash_file(dataset):
        raise ValueError("Frozen metrics dataset mismatch")
    if any(output_dir.glob("ridge*")):
        raise FileExistsError("Ridge artifacts exist; use a fresh --output-dir")
    selection = select_alpha(training)
    pipeline = build_pipeline(selection["selected_alpha"])
    pipeline.fit(select_features(training), training[TARGET])
    predictions, evaluation = evaluate_pipeline(pipeline, testing, float(training[TARGET].median()))
    coefficients = extract_coefficients(pipeline)
    comparison = {
        "mae_improvement_eur": baseline["metrics"]["mae"] - evaluation["metrics"]["mae"],
        "rmse_improvement_eur": baseline["metrics"]["rmse"] - evaluation["metrics"]["rmse"],
        "r2_change": evaluation["metrics"]["r2"] - baseline["metrics"]["r2"],
    }
    metadata = {
        "schema_version": 1,
        "model_name": "ridge",
        "model_type": "sklearn.linear_model.Ridge",
        "status": "experiment_not_production",
        "feature_names": FEATURES,
        "target": TARGET,
        "target_transform": "none",
        "preprocessing": "StandardScaler fitted inside each training pipeline; no imputation",
        "training_seasons": list(TRAIN_SEASONS),
        "testing_season": TEST_SEASON,
        "split_strategy": "temporal",
        "training_rows": len(training),
        "testing_rows": len(testing),
        "rows_dropped": 0,
        "dataset": baseline["dataset"],
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "numpy_version": np.__version__,
        "alpha_selection": selection,
        "model_parameters": pipeline.named_steps["ridge"].get_params(),
        "frozen_baseline_hashes": frozen,
        "code_hashes": {
            name: hash_file(Path(__file__).with_name(name)) for name in ("ridge.py", "baseline.py")
        },
        "residual_convention": "actual - predicted",
        "prediction_postprocessing": "none; negative predictions retained",
        "comparison_to_linear_regression": comparison,
        **coefficients,
        **evaluation,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_dir / "ridge.joblib")
    predictions.to_csv(output_dir / "ridge_test_predictions.csv", index=False, lineterminator="\n")
    metadata["model_sha256"] = hash_file(output_dir / "ridge.joblib")
    metadata["predictions_sha256"] = hash_file(output_dir / "ridge_test_predictions.csv")
    entries = [entry for entry in entries if entry["model"] != "ridge"]
    entries.append(
        {
            "model": "ridge",
            **evaluation["metrics"],
            "alpha": selection["selected_alpha"],
            "split_strategy": "temporal",
            "training_seasons": list(TRAIN_SEASONS),
            "testing_season": TEST_SEASON,
            "dataset_sha256": hash_file(dataset),
        }
    )
    for name, payload in {
        "ridge_metadata.json": metadata,
        "ridge_coefficients.json": coefficients,
        "ridge_analysis.json": prediction_analysis(predictions),
        "model_metrics.json": entries,
    }.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    if any(hash_file(baseline_dir / name) != digest for name, digest in frozen.items()):
        raise RuntimeError("Frozen baseline was changed")
    return metadata


def evaluate_saved(dataset: Path, model_path: Path) -> dict:
    metadata = json.loads(model_path.with_name("ridge_metadata.json").read_text())
    if hash_file(dataset) != metadata["dataset"]["sha256"]:
        raise ValueError("Dataset differs from training")
    if hash_file(model_path) != metadata["model_sha256"]:
        raise ValueError("Model hash mismatch")
    _, testing = temporal_split(load_dataset(dataset))
    pipeline = joblib.load(model_path)
    extract_coefficients(pipeline)
    _, evaluation = evaluate_pipeline(
        pipeline, testing, metadata["median_baseline"]["training_median_eur"]
    )
    return evaluation


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
            result = {
                key: result[key]
                for key in (
                    "alpha_selection",
                    "metrics",
                    "comparison_to_linear_regression",
                    "negative_prediction_count",
                )
            }
        else:
            result = evaluate_saved(args.dataset, args.output_dir / "ridge.joblib")
    except (ValueError, OSError) as error:
        parser.exit(2, f"Ridge failed: {error}\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
