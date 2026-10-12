"""Train only the Session 3 Linear Regression temporal baseline."""

import argparse
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn

from .baseline import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    FEATURES,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    build_pipeline,
    evaluate_pipeline,
    extract_coefficients,
    inspect_dataset,
    load_dataset,
    prediction_analysis,
    select_features,
    temporal_split,
)
from .data_pipeline.ingestion import hash_file


def train(dataset: Path, output_dir: Path) -> dict[str, Any]:
    frame = load_dataset(dataset)
    training, testing = temporal_split(frame)
    dataset_hash = hash_file(dataset)
    provenance: dict[str, Any] = {"filename": dataset.name, "sha256": dataset_hash}
    cleaning_path = dataset.with_name("cleaning_report.json")
    if cleaning_path.exists():
        cleaning = json.loads(cleaning_path.read_text(encoding="utf-8"))
        if cleaning.get("output_sha256") != dataset_hash:
            raise ValueError("Dataset hash does not match its cleaning report")
        provenance.update(
            cleaning_report_sha256=hash_file(cleaning_path),
            source_provenance=cleaning.get("provenance"),
            source_limitations=cleaning.get("unresolved_data_quality_issues", []),
        )
    names = [
        "linear_regression.joblib",
        "linear_regression_metadata.json",
        "linear_regression_coefficients.json",
        "linear_regression_test_predictions.csv",
        "linear_regression_analysis.json",
        "model_metrics.json",
    ]
    if any((output_dir / name).exists() for name in names):
        raise FileExistsError("Baseline outputs already exist; select a fresh --output-dir")
    pipeline = build_pipeline()
    pipeline.fit(select_features(training), training[TARGET])
    median = float(training[TARGET].median())
    predictions, evaluation = evaluate_pipeline(pipeline, testing, median)
    coefficients = extract_coefficients(pipeline)
    metadata = {
        "schema_version": 1,
        "model_name": "linear_regression",
        "model_type": "sklearn.linear_model.LinearRegression",
        "status": "baseline_not_production",
        "feature_names": FEATURES,
        "target": TARGET,
        "target_transform": "none",
        "preprocessing": "No scaling/imputation; missing or invalid values fail validation",
        "split_strategy": "temporal",
        "training_seasons": list(TRAIN_SEASONS),
        "testing_season": TEST_SEASON,
        "training_rows": len(training),
        "testing_rows": len(testing),
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sklearn_version": sklearn.__version__,
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "joblib": joblib.__version__,
        },
        "model_parameters": pipeline.named_steps["linear_regression"].get_params(),
        "dataset": provenance,
        "dataset_inspection": inspect_dataset(frame),
        "residual_convention": "actual - predicted",
        "prediction_postprocessing": "none; negative predictions are retained and counted",
        "code_hashes": {
            name: hash_file(Path(__file__).with_name(name))
            for name in ("train.py", "baseline.py", "evaluate.py")
        },
        **coefficients,
        **evaluation,
    }
    if "market_value_days_from_season_end" in frame:
        metadata["pre_end_target_rows"] = {
            "train": int(training["market_value_days_from_season_end"].lt(0).sum()),
            "test": int(testing["market_value_days_from_season_end"].lt(0).sum()),
        }
    metadata["test_players_seen_in_training"] = int(
        testing["player_id"].isin(training["player_id"]).sum()
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / names[0]
    joblib.dump(pipeline, model_path)
    metadata["model_sha256"] = hash_file(model_path)
    predictions.to_csv(output_dir / names[3], index=False, lineterminator="\n")
    metadata["predictions_sha256"] = hash_file(output_dir / names[3])
    documents = {
        names[1]: metadata,
        names[2]: coefficients,
        names[4]: prediction_analysis(predictions),
        names[5]: [
            {
                "model": "linear_regression",
                **evaluation["metrics"],
                "split_strategy": "temporal",
                "testing_season": TEST_SEASON,
                "training_seasons": list(TRAIN_SEASONS),
                "dataset_sha256": dataset_hash,
            }
        ],
    }
    for name, payload in documents.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["linear"], default="linear")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        metadata = train(args.dataset, args.output_dir)
    except (ValueError, OSError) as error:
        parser.exit(2, f"Training failed: {error}\n")
    print(
        json.dumps(
            {
                key: metadata[key]
                for key in (
                    "training_rows",
                    "testing_rows",
                    "metrics",
                    "median_baseline",
                    "negative_prediction_count",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
