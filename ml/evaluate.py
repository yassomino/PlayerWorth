"""Reload and evaluate the saved baseline on its unchanged temporal holdout, without fitting."""

import argparse
import json
from pathlib import Path
from typing import Any

import joblib

from .baseline import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    FEATURES,
    TEST_SEASON,
    TRAIN_SEASONS,
    evaluate_pipeline,
    extract_coefficients,
    load_dataset,
    temporal_split,
)
from .data_pipeline.ingestion import hash_file


def evaluate_saved(dataset: Path, model_path: Path) -> dict[str, Any]:
    metadata = json.loads(
        model_path.with_name("linear_regression_metadata.json").read_text(encoding="utf-8")
    )
    if hash_file(dataset) != metadata["dataset"]["sha256"]:
        raise ValueError("Dataset differs from the saved evaluation dataset")
    if hash_file(model_path) != metadata["model_sha256"]:
        raise ValueError("Model artifact differs from its metadata")
    if (
        metadata["feature_names"] != FEATURES
        or metadata["training_seasons"] != list(TRAIN_SEASONS)
        or metadata["testing_season"] != TEST_SEASON
    ):
        raise ValueError("Saved model does not match the Session 3 feature/split contract")
    _, test = temporal_split(load_dataset(dataset))
    # Load only this project's trusted, locally generated artifact.
    pipeline = joblib.load(model_path)
    extract_coefficients(pipeline)
    _, result = evaluate_pipeline(
        pipeline, test, metadata["median_baseline"]["training_median_eur"]
    )
    return {
        "model_name": metadata["model_name"],
        "testing_season": TEST_SEASON,
        "testing_rows": len(test),
        "dataset_sha256": metadata["dataset"]["sha256"],
        **result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--model-path", type=Path, default=DEFAULT_OUTPUT / "linear_regression.joblib"
    )
    args = parser.parse_args()
    try:
        result = evaluate_saved(args.dataset, args.model_path)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Evaluation failed: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
