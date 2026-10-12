"""Validated single and batch inference for the PlayerWorth V1 production candidate."""

import argparse
import json
from collections.abc import Mapping
from numbers import Real
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .baseline import DEFAULT_OUTPUT
from .data_pipeline.ingestion import hash_file
from .xgboost_position import INPUTS


def validate_inputs(rows) -> pd.DataFrame:
    if isinstance(rows, Mapping):
        rows = [rows]
    if not isinstance(rows, pd.DataFrame):
        rows = list(rows)
        if not rows or any(not isinstance(row, Mapping) or set(row) != set(INPUTS) for row in rows):
            raise ValueError(f"Every row must contain exactly {INPUTS}")
    frame = pd.DataFrame(rows).copy()
    if frame.empty or frame.columns.duplicated().any() or set(frame.columns) != set(INPUTS):
        raise ValueError(f"Inputs must contain exactly {INPUTS} and at least one row")
    for name in INPUTS[:-1]:
        if any(
            isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
            for value in frame[name]
        ):
            raise ValueError(f"{name} must be numeric (not bool or a string)")
        values = frame[name].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"{name} must be finite and nonnegative")
        if name in ("goals", "assists") and (values != np.floor(values)).any():
            raise ValueError(f"{name} must be integer-compatible")
        frame[name] = values
    for value in frame.position:
        if not isinstance(value, str) and not pd.isna(value):
            raise ValueError("position must be a string or missing value")
    return frame[INPUTS]


def load_model(path: Path | str | None = None):
    if path is None:
        pointer = json.loads((DEFAULT_OUTPUT / "current_model.json").read_text())
        if pointer["model_name"] != "playerworth_v1":
            raise ValueError("Unexpected current model")
        artifact = Path(pointer["artifact"])
        if artifact.name != str(artifact):
            raise ValueError("Current model artifact must be a relative filename")
        path = DEFAULT_OUTPUT / artifact
    path = Path(path)
    metadata = json.loads(path.with_name("playerworth_v1_metadata.json").read_text())
    if metadata["features"] != INPUTS or metadata["model_name"] != "playerworth_v1":
        raise ValueError("Model contract mismatch")
    if hash_file(path) != metadata["artifact_sha256"]:
        raise ValueError("Model artifact hash mismatch")
    model = joblib.load(path)
    if list(model.feature_names_in_) != INPUTS:
        raise ValueError("Serialized feature contract mismatch")
    return model


def predict_batch(rows, *, model=None, model_path: Path | str | None = None) -> np.ndarray:
    frame = validate_inputs(rows)
    if model is None:
        model = load_model(model_path)
    predictions = np.asarray(model.predict(frame), dtype=float)
    if predictions.shape != (len(frame),) or not np.isfinite(predictions).all():
        raise ValueError("Model returned invalid predictions")
    return predictions


def predict_player_value(
    *, age, minutes, goals, assists, position, model=None, model_path: Path | str | None = None
) -> float:
    return float(
        predict_batch(
            dict(age=age, minutes=minutes, goals=goals, assists=assists, position=position),
            model=model,
            model_path=model_path,
        )[0]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in INPUTS[:-1]:
        parser.add_argument("--" + name, type=float, required=True)
    parser.add_argument("--position", required=True)
    parser.add_argument("--model-path", type=Path)
    args = parser.parse_args()
    print(json.dumps({"predicted_market_value_eur": predict_player_value(**vars(args))}))


if __name__ == "__main__":
    main()
