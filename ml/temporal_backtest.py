"""Expanding-window evaluation of two frozen XGBoost experiment definitions."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import sklearn
import xgboost

from .baseline import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    TARGET,
    TEST_SEASON,
    TRAIN_SEASONS,
    load_dataset,
    prediction_table,
    regression_metrics,
    select_features,
)
from .data_pipeline.ingestion import hash_file
from .xgboost_model import build_pipeline as numeric_pipeline
from .xgboost_position import PARAMETERS, ROUNDS, build_pipeline, error_summary, evaluate, inputs

SEASONS = (*TRAIN_SEASONS, TEST_SEASON)
MODELS = ("xgboost_4_features", "xgboost_with_position")
DEFAULT_EVALUATION = Path(__file__).parent / "evaluation"
OUTPUT_NAMES = (
    "temporal_backtest_summary.json",
    "temporal_backtest_predictions.csv",
    "temporal_backtest_fold_metrics.csv",
)


def expanding_folds(frame: pd.DataFrame):
    """Require the declared cohort; never silently filter unexpected seasons."""
    if set(frame.season) != set(SEASONS):
        raise ValueError("Expected exactly the five declared seasons")
    for index in range(1, len(SEASONS)):
        training = frame.loc[frame.season.isin(SEASONS[:index])].copy()
        testing = frame.loc[frame.season.eq(SEASONS[index])].copy()
        yield index, SEASONS[:index], SEASONS[index], training, testing


def backtest(
    frame: pd.DataFrame, definitions: dict | None = None
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    models = tuple(definitions) if definitions is not None else MODELS
    if len(models) != 2:
        raise ValueError("Backtesting compares exactly two definitions")
    predictions, metrics, encoder_audit = [], [], []
    for fold, train_seasons, test_season, training, testing in expanding_folds(frame):
        for name in models:
            if definitions is not None:
                factory, selector, evaluator = definitions[name]
                model = factory()
                model.fit(selector(training), training[TARGET])
                result, _ = evaluator(model, testing)
            elif name == "xgboost_4_features":
                model = numeric_pipeline(PARAMETERS, ROUNDS)
                model.fit(select_features(training), training[TARGET])
                result = prediction_table(model, testing)
            else:
                model = build_pipeline()
                model.fit(inputs(training), training[TARGET])
                result, _ = evaluate(model, testing)
                encoder = model.named_steps["preprocess"].named_transformers_["categorical"]
                encoder_audit.append(
                    {
                        "fold": fold,
                        "training_categories": encoder.named_steps["encode"]
                        .categories_[0]
                        .tolist(),
                    }
                )
            scores = regression_metrics(
                result.actual_market_value_eur, result.predicted_market_value_eur
            )
            context = {
                "model_name": name,
                "fold": fold,
                "train_seasons": "|".join(train_seasons),
                "test_season": test_season,
            }
            metrics.append(
                {
                    **context,
                    "training_rows": len(training),
                    "test_rows": len(testing),
                    **scores,
                    **error_summary(result),
                }
            )
            for key, value in context.items():
                result[key] = value
            predictions.append(result)
    pooled = pd.concat(predictions, ignore_index=True)
    fold_metrics = pd.DataFrame(metrics)
    aggregates = {}
    for name in models:
        folds = fold_metrics.loc[fold_metrics.model_name.eq(name)]
        rows = pooled.loc[pooled.model_name.eq(name)]
        # Undefined R2 remains null rather than averaging an unreported subset of folds.
        aggregates[name] = {
            "average_of_folds": {
                "mean_mae": float(folds.mae.mean()),
                "median_mae": float(folds.mae.median()),
                "mean_rmse": float(folds.rmse.mean()),
                "mean_r2": float(folds.r2.mean()) if folds.r2.notna().all() else None,
                "mean_median_absolute_error_eur": float(folds.median_absolute_error_eur.mean()),
            },
            "pooled": {
                "rows": len(rows),
                **regression_metrics(rows.actual_market_value_eur, rows.predicted_market_value_eur),
                **error_summary(rows),
            },
        }
    comparisons = []
    for fold in range(1, 5):
        pair = fold_metrics.loc[fold_metrics.fold.eq(fold)].set_index("model_name")
        old, new = pair.loc[models[0]], pair.loc[models[1]]
        difference = float(new.mae - old.mae)
        comparisons.append(
            {
                "fold": fold,
                "test_season": new.test_season,
                "mae_difference_eur": difference,
                "mae_percentage_difference": 100 * difference / old.mae if old.mae else None,
                "rmse_difference_eur": float(new.rmse - old.rmse),
                "r2_difference": float(new.r2 - old.r2)
                if pd.notna(new.r2) and pd.notna(old.r2)
                else None,
            }
        )
    counts = {
        "mae_improves": sum(row["mae_difference_eur"] < 0 for row in comparisons),
        "mae_worsens": sum(row["mae_difference_eur"] > 0 for row in comparisons),
        "mae_ties": sum(row["mae_difference_eur"] == 0 for row in comparisons),
        "rmse_improves": sum(row["rmse_difference_eur"] < 0 for row in comparisons),
        "r2_improves": sum(
            row["r2_difference"] is not None and row["r2_difference"] > 0 for row in comparisons
        ),
    }
    summary = {
        "aggregates": aggregates,
        "comparisons": comparisons,
        "position_season_counts": counts,
        "encoder_audit": encoder_audit,
        "fold_metrics": json.loads(fold_metrics.to_json(orient="records", double_precision=15)),
    }
    columns = [
        "model_name",
        "fold",
        "train_seasons",
        "test_season",
        "player_id",
        "player_name",
        "position",
        "actual_market_value_eur",
        "predicted_market_value_eur",
        "residual_eur",
        "absolute_error_eur",
    ]
    return summary, pooled[columns], fold_metrics


def run(dataset: Path, output_dir: Path, models_dir: Path = DEFAULT_OUTPUT) -> dict:
    if output_dir.resolve() == models_dir.resolve():
        raise ValueError("Evaluation output must be separate from model artifacts")
    if any((output_dir / name).exists() for name in OUTPUT_NAMES):
        raise FileExistsError("Evaluation outputs exist; choose a fresh --output-dir")
    frozen = {
        str(path.resolve()): hash_file(path) for path in models_dir.glob("*") if path.is_file()
    }
    dataset_hash = hash_file(dataset)
    summary, predictions, metrics = backtest(load_dataset(dataset))
    if hash_file(dataset) != dataset_hash or any(
        hash_file(Path(path)) != digest for path, digest in frozen.items()
    ):
        raise RuntimeError("Dataset or previous artifacts changed")
    summary.update(
        schema_version=1,
        dataset_sha256=dataset_hash,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        frozen_parameters={
            **PARAMETERS,
            "n_estimators": ROUNDS,
            "random_state": 42,
            "objective": "reg:squarederror",
            "tree_method": "hist",
            "n_jobs": 1,
        },
        versions={
            "xgboost": xgboost.__version__,
            "sklearn": sklearn.__version__,
            "numpy": np.__version__,
        },
        prior_artifact_hashes=frozen,
        residual_convention="actual - predicted",
        comparison_convention="position minus four features; negative MAE means improvement",
        limitations=[
            "2025/26 repeatedly inspected: exploratory held-out season",
            "Frozen hyperparameters selected using 2024/25; retrospective, not nested selection",
            "Position is historically unverified snapshot metadata",
            "Only four overlapping-training folds; repeated players; no significance test",
        ],
        code_hashes={
            name: hash_file(Path(__file__).with_name(name))
            for name in (
                "temporal_backtest.py",
                "xgboost_model.py",
                "xgboost_position.py",
                "baseline.py",
            )
        },
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output_dir / OUTPUT_NAMES[1], index=False, lineterminator="\n")
    metrics.to_csv(output_dir / OUTPUT_NAMES[2], index=False, lineterminator="\n")
    summary["output_hashes"] = {name: hash_file(output_dir / name) for name in OUTPUT_NAMES[1:]}
    (output_dir / OUTPUT_NAMES[0]).write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVALUATION)
    args = parser.parse_args()
    result = run(args.dataset, args.output_dir)
    print(
        json.dumps(
            {key: result[key] for key in ("aggregates", "comparisons", "position_season_counts")},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
