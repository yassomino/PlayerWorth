"""Fixed-configuration position experiment; no tuning or source dataset changes."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder

from .baseline import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    FEATURES,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    load_dataset,
    prediction_analysis,
    regression_metrics,
    select_features,
    temporal_split,
)
from .data_pipeline.ingestion import hash_file
from .preprocessing.position import POSITIONS, normalize_position
from .xgboost_model import build_pipeline as numeric_pipeline

INPUTS = [*FEATURES, "position"]
PARAMETERS = dict(
    max_depth=4, learning_rate=0.1, min_child_weight=5, subsample=0.8, colsample_bytree=0.8
)
ROUNDS = 63
STEM = "xgboost_position"


def inputs(frame: pd.DataFrame) -> pd.DataFrame:
    selected = select_features(frame)
    selected["position"] = frame["position"]
    return selected


def build_pipeline() -> Pipeline:
    categorical = Pipeline(
        [
            ("normalize", FunctionTransformer(normalize_position, feature_names_out="one-to-one")),
            ("encode", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    preprocess = ColumnTransformer(
        [
            ("numeric", "passthrough", FEATURES),
            ("categorical", categorical, ["position"]),
        ],
        verbose_feature_names_out=False,
    )
    estimator = numeric_pipeline(PARAMETERS, ROUNDS).named_steps["xgboost"]
    return Pipeline([("preprocess", preprocess), ("xgboost", estimator)])


def feature_importance(model: Pipeline) -> dict:
    names = model.named_steps["preprocess"].get_feature_names_out().tolist()
    values = model.named_steps["xgboost"].feature_importances_.tolist()
    mapped = dict(zip(names, values, strict=True))
    return {
        "method": "gain",
        "normalization": "normalized average split gain",
        "transformed_feature_names": names,
        "importances": dict(sorted(mapped.items(), key=lambda pair: pair[1], reverse=True)),
        "position_family_importance": sum(
            v for k, v in mapped.items() if k.startswith("position_")
        ),
    }


def error_summary(predictions: pd.DataFrame) -> dict:
    return {
        "negative_prediction_count": int(predictions.predicted_market_value_eur.lt(0).sum()),
        "minimum_prediction_eur": float(predictions.predicted_market_value_eur.min()),
        "maximum_prediction_eur": float(predictions.predicted_market_value_eur.max()),
        "median_absolute_error_eur": float(predictions.absolute_error_eur.median()),
        "worst_absolute_error_eur": float(predictions.absolute_error_eur.max()),
    }


def position_metrics(predictions: pd.DataFrame) -> list[dict]:
    rows = []
    for position in POSITIONS:
        group = predictions.loc[predictions.position.eq(position)]
        scores = (
            regression_metrics(group.actual_market_value_eur, group.predicted_market_value_eur)
            if len(group)
            else {}
        )
        rows.append(
            {
                "position": position,
                "n": len(group),
                "mae": scores.get("mae"),
                "median_absolute_error_eur": float(group.absolute_error_eur.median())
                if len(group)
                else None,
                "rmse": scores.get("rmse") if len(group) >= 5 else None,
            }
        )
    return rows


def evaluate(model: Pipeline, testing: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    predicted = np.asarray(model.predict(inputs(testing)), dtype=float)
    scores = regression_metrics(testing[TARGET], predicted)
    result = testing[["player_id", "player_name", "season", "position", *FEATURES]].copy()
    result["position"] = normalize_position(result[["position"]])["position"]
    result["actual_market_value_eur"] = testing[TARGET]
    result["predicted_market_value_eur"] = predicted
    result["residual_eur"] = result.actual_market_value_eur - predicted
    result["absolute_error_eur"] = result.residual_eur.abs()
    return result, scores


def train(dataset: Path, output_dir: Path, baseline_dir: Path = DEFAULT_OUTPUT) -> dict:
    frame = load_dataset(dataset)
    training, testing = temporal_split(frame)
    baseline = json.loads((baseline_dir / "xgboost_metadata.json").read_text())
    digest = hash_file(dataset)
    if (
        baseline["dataset"]["sha256"] != digest
        or baseline["feature_names"] != FEATURES
        or baseline["selected_parameters"] != PARAMETERS
        or baseline["effective_rounds"] != ROUNDS
        or baseline["training_seasons"] != list(TRAIN_SEASONS)
        or baseline["testing_season"] != TEST_SEASON
        or baseline["training_rows"] != len(training)
        or baseline["testing_rows"] != len(testing)
    ):
        raise ValueError("Frozen baseline dataset/configuration/split mismatch")
    # Exact filenames avoid capturing this experiment on a later repeat run.
    frozen = {}
    for name in ("linear_regression", "ridge", "random_forest", "xgboost"):
        for suffix in (
            ".joblib",
            "_metadata.json",
            "_coefficients.json",
            "_feature_importance.json",
            "_test_predictions.csv",
            "_analysis.json",
        ):
            path = baseline_dir / (name + suffix)
            if path.exists():
                frozen[path.name] = hash_file(path)
    if (
        frozen["xgboost.joblib"] != baseline["model_sha256"]
        or frozen["xgboost_test_predictions.csv"] != baseline["predictions_sha256"]
    ):
        raise ValueError("Frozen baseline artifact mismatch")
    metrics_path = output_dir / "model_metrics.json"
    entries = json.loads(
        (metrics_path if metrics_path.exists() else baseline_dir / "model_metrics.json").read_text()
    )
    old_entry = [entry for entry in entries if entry["model"] == "xgboost"]
    if len(old_entry) != 1 or any(
        old_entry[0][key] != val for key, val in baseline["metrics"].items()
    ):
        raise ValueError("Frozen metrics mismatch")
    if any(output_dir.glob(STEM + "*")):
        raise FileExistsError("Position artifacts exist; use a fresh --output-dir")
    model = build_pipeline().fit(inputs(training), training[TARGET])
    predictions, scores = evaluate(model, testing)
    old = pd.read_csv(baseline_dir / "xgboost_test_predictions.csv", dtype={"player_id": str})
    identity = ["player_id", "season", *FEATURES, "actual_market_value_eur"]
    pd.testing.assert_frame_equal(
        predictions[identity].reset_index(drop=True), old[identity], check_dtype=False
    )
    old["position"] = predictions.position.to_numpy()
    comparison = {
        "mae_improvement_eur": baseline["metrics"]["mae"] - scores["mae"],
        "mae_improvement_percent": 100
        * (baseline["metrics"]["mae"] - scores["mae"])
        / baseline["metrics"]["mae"],
        "rmse_improvement_eur": baseline["metrics"]["rmse"] - scores["rmse"],
        "r2_change": scores["r2"] - baseline["metrics"]["r2"],
    }
    focus = predictions[
        predictions.player_id.isin(["418560", "495666", "357662", "687626", "568177"])
    ].merge(
        old[["player_id", "predicted_market_value_eur", "absolute_error_eur"]].rename(
            columns={
                "predicted_market_value_eur": "old_prediction_eur",
                "absolute_error_eur": "old_absolute_error_eur",
            }
        ),
        on="player_id",
        validate="one_to_one",
    )
    analysis = {
        **prediction_analysis(predictions),
        **error_summary(predictions),
        "old_error_summary": error_summary(old),
        "by_position": position_metrics(predictions),
        "old_by_position": position_metrics(old),
        "named_players": focus.to_dict("records"),
    }
    counts = {
        name: normalize_position(group[["position"]]).position.value_counts().sort_index().to_dict()
        for name, group in (("overall", frame), ("training", training), ("test", testing))
    }
    importance = feature_importance(model)
    metadata = {
        "model_name": "xgboost_with_position",
        "model_type": "xgboost.XGBRegressor",
        "feature_names": INPUTS,
        "target": TARGET,
        "training_rows": len(training),
        "testing_rows": len(testing),
        "training_seasons": list(TRAIN_SEASONS),
        "testing_season": TEST_SEASON,
        "selected_parameters": PARAMETERS,
        "effective_rounds": ROUNDS,
        "random_state": 42,
        "objective": "reg:squarederror",
        "selection": "none; frozen Session 6 configuration",
        "dataset": baseline["dataset"],
        "metrics": scores,
        "comparison": comparison,
        "position_counts": counts,
        "rows_dropped": 0,
        "position_limitation": "Undated snapshot metadata; historical validity unverified",
        "unknown_policy": "Missing/unmapped -> UNKNOWN; unseen encoder category -> all zeros",
        "transformed_feature_names": importance["transformed_feature_names"],
        "frozen_artifact_hashes": frozen,
        "xgboost_version": xgboost.__version__,
        "sklearn_version": sklearn.__version__,
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "code_hashes": {
            name: hash_file(Path(__file__).with_name(name))
            for name in ("xgboost_position.py", "xgboost_model.py", "baseline.py")
        },
        "residual_convention": "actual - predicted",
        "status": "experiment_not_production",
        **error_summary(predictions),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / (STEM + ".joblib"))
    predictions.to_csv(
        output_dir / (STEM + "_test_predictions.csv"), index=False, lineterminator="\n"
    )
    metadata["model_sha256"] = hash_file(output_dir / (STEM + ".joblib"))
    metadata["predictions_sha256"] = hash_file(output_dir / (STEM + "_test_predictions.csv"))
    # Preserve stable model identifier and previous results; add a descriptive comparison label.
    old_entry[0]["comparison_name"] = "xgboost_4_features"
    entries = [e for e in entries if e["model"] != "xgboost_with_position"]
    entries.append(
        {
            "model": "xgboost_with_position",
            "comparison_name": "xgboost_with_position",
            **scores,
            "dataset_sha256": digest,
            "training_seasons": list(TRAIN_SEASONS),
            "testing_season": TEST_SEASON,
            "feature_names": INPUTS,
        }
    )
    for name, payload in {
        STEM + "_metadata.json": metadata,
        STEM + "_analysis.json": analysis,
        STEM + "_feature_importance.json": importance,
        "model_metrics.json": entries,
    }.items():
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    if hash_file(dataset) != digest or any(
        hash_file(baseline_dir / name) != val for name, val in frozen.items()
    ):
        raise RuntimeError("Frozen inputs changed")
    return metadata


def evaluate_saved(dataset: Path, model_path: Path) -> dict:
    metadata = json.loads(model_path.with_name(STEM + "_metadata.json").read_text())
    if (
        hash_file(dataset) != metadata["dataset"]["sha256"]
        or hash_file(model_path) != metadata["model_sha256"]
    ):
        raise ValueError("Dataset/model hash mismatch")
    _, testing = temporal_split(load_dataset(dataset))
    return evaluate(joblib.load(model_path), testing)[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["train", "evaluate"])
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.action == "train":
        result = train(args.dataset, args.output_dir, args.baseline_dir)
        result = {key: result[key] for key in ("metrics", "comparison", "position_counts")}
    else:
        result = evaluate_saved(args.dataset, args.output_dir / (STEM + ".joblib"))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
