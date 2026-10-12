"""All-data V1 deployment fit; evaluation is inherited OOF evidence, never fit scores."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import sklearn
import xgboost

from .baseline import DEFAULT_DATASET, DEFAULT_OUTPUT, TARGET, load_dataset
from .data_pipeline.ingestion import hash_file
from .inference import validate_inputs
from .temporal_backtest import DEFAULT_EVALUATION, SEASONS
from .xgboost_position import INPUTS, PARAMETERS, ROUNDS, build_pipeline, feature_importance

NAMES = (
    "playerworth_v1.joblib",
    "playerworth_v1_metadata.json",
    "playerworth_v1_feature_importance.json",
    "current_model.json",
)


def freeze(
    dataset: Path,
    output_dir: Path,
    evidence_dir: Path = DEFAULT_EVALUATION,
    prior_models: Path = DEFAULT_OUTPUT,
    expected_rows: int = 2594,
) -> dict:
    if any((output_dir / name).exists() for name in NAMES):
        raise FileExistsError("V1 outputs exist; choose a fresh --output-dir")
    if xgboost.__version__ != "3.4.1":
        raise ValueError("V1 requires the pinned XGBoost 3.4.1 environment")
    frozen = {
        str(p.resolve()): hash_file(p)
        for folder in (prior_models, evidence_dir)
        for p in folder.glob("*")
        if p.is_file()
    }
    digest = hash_file(dataset)
    frame = load_dataset(dataset)
    if len(frame) != expected_rows or set(frame.season) != set(SEASONS):
        raise ValueError("Unexpected all-data cohort size or seasons")
    evidence_path = evidence_dir / "temporal_backtest_summary.json"
    evidence = json.loads(evidence_path.read_text())
    if evidence["dataset_sha256"] != digest:
        raise ValueError("Backtest evidence belongs to a different dataset")
    for name, checksum in evidence["output_hashes"].items():
        if hash_file(evidence_dir / name) != checksum:
            raise ValueError("Backtest evidence hash mismatch")
    for name, value in {**PARAMETERS, "n_estimators": ROUNDS, "random_state": 42}.items():
        if evidence["frozen_parameters"][name] != value:
            raise ValueError("Backtest configuration mismatch")
    model = build_pipeline().fit(validate_inputs(frame[INPUTS]), frame[TARGET])
    importance = feature_importance(model)
    provenance = {"filename": dataset.name, "sha256": digest}
    cleaning = dataset.with_name("cleaning_report.json")
    if cleaning.exists():
        report = json.loads(cleaning.read_text())
        if report["output_sha256"] != digest:
            raise ValueError("Cleaning report mismatch")
        provenance.update(
            cleaning_report_sha256=hash_file(cleaning), source_provenance=report.get("provenance")
        )
    metadata = {
        "model_name": "playerworth_v1",
        "model_version": "1.0.0",
        "model_type": "xgboost.XGBRegressor",
        "artifact_purpose": "PlayerWorth V1 production candidate",
        "features": INPUTS,
        "target": TARGET,
        "target_transform": "none",
        "deployment_training_rows": len(frame),
        "training_seasons": list(SEASONS),
        "season_counts": frame.season.value_counts().sort_index().to_dict(),
        "dataset": provenance,
        "xgboost_version": xgboost.__version__,
        "sklearn_version": sklearn.__version__,
        "random_state": 42,
        "hyperparameters": {
            **PARAMETERS,
            "n_estimators": ROUNDS,
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "device": "cpu",
            "n_jobs": 1,
        },
        "position_preprocessing": (
            "Strip/uppercase; missing/blank/unmapped -> UNKNOWN; "
            "train-fitted OneHotEncoder(handle_unknown=ignore, sparse_output=False)"
        ),
        "transformed_feature_names": importance["transformed_feature_names"],
        "training_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation": {
            "scope": "temporal out-of-fold backtest; NOT final-model test performance",
            "pooled": evidence["aggregates"]["xgboost_with_position"]["pooled"],
            "average_of_folds": evidence["aggregates"]["xgboost_with_position"]["average_of_folds"],
            "fold_metrics": [
                r for r in evidence["fold_metrics"] if r["model_name"] == "xgboost_with_position"
            ],
            "position_consistency": evidence["position_season_counts"],
            "source_sha256": hash_file(evidence_path),
        },
        "final_fit_test_metrics": None,
        "known_limitations": evidence["limitations"]
        + [
            "All five seasons used for deployment fit; no unseen season remains",
            "EPL only; omitted market/contract/injury/club context; large individual errors",
            "Raw predictions can be negative; no clipping or confidence scores",
        ],
        "rejected_features": {
            "goals_per_90": "MAE worsened in 4/4 folds",
            "assists_per_90": "MAE worsened in 4/4 folds",
        },
        "prior_artifact_hashes": frozen,
        "code_hashes": {
            name: hash_file(Path(__file__).with_name(name))
            for name in ("freeze_v1.py", "inference.py", "xgboost_position.py", "xgboost_model.py")
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_dir / NAMES[0])
    metadata["artifact_sha256"] = hash_file(output_dir / NAMES[0])
    pointer = {
        "model_name": "playerworth_v1",
        "model_version": "1.0.0",
        "artifact": NAMES[0],
        "metadata": NAMES[1],
    }
    for name, payload in ((NAMES[1], metadata), (NAMES[2], importance), (NAMES[3], pointer)):
        (output_dir / name).write_text(
            json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
    if hash_file(dataset) != digest or any(hash_file(Path(p)) != val for p, val in frozen.items()):
        raise RuntimeError("Frozen dataset or previous artifacts changed")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = freeze(DEFAULT_DATASET, args.output_dir)
    print(
        json.dumps(
            {
                key: result[key]
                for key in (
                    "model_name",
                    "model_version",
                    "deployment_training_rows",
                    "training_seasons",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
