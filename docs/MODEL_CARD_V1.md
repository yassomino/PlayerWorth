# PlayerWorth V1 model card

**Model:** playerworth_v1, version 1.0.0. **Purpose:** PlayerWorth V1 production candidate. The ML layer is frozen; this artifact is not yet deployed behind an API.

## Purpose and output

Estimate end-of-season Premier League player market value from a small set of performance/context inputs. The output is a raw numeric estimate in EUR, not an actual transfer fee or objective true value. Inputs are age, minutes, goals, assists and position. The precise validation rules and single/batch inference examples are in [ML_INPUT_V1.md](ML_INPUT_V1.md).

## Data and deployment training

The deployment model is newly trained on all 2,594 retained Transfermarkt-derived player-season rows: 2021/22 (491), 2022/23 (522), 2023/24 (534), 2024/25 (543), 2025/26 (504). Matches contribute only to their exact season. Historical age is measured at season end. Targets are the first observed valuation on or after the final Premier League match, within 45 days. Rows without eligible targets were excluded upstream.

Position comes from an undated snapshot and is not independently verified as historical. Source licensing/archive provenance and provider accuracy are not fully verified. The valuation export does not cover the entire configured 2025/26 post-season window. Dataset provenance and hashes are preserved in metadata.

**The all-data deployment fit has no unseen season remaining. No training-fit scores are reported as test performance.** All reported evaluation evidence below comes from earlier temporal out-of-fold fits, not the final deployment model.

## Frozen model and preprocessing

XGBoost 3.4.1; reg:squarederror; max_depth=4; learning_rate=0.1; min_child_weight=5; subsample=0.8; colsample_bytree=0.8; 63 boosting rounds; random_state=42; CPU hist; n_jobs=1. No tuning, early stopping, target transform or feature change occurs during final fitting.

Four numerical features pass through unchanged. Position is stripped/uppercased, missing/blank/unmapped values become UNKNOWN, and OneHotEncoder(handle_unknown="ignore", sparse_output=False) encodes it. Preprocessing and estimator are serialized together; no scaler is used.

## Selection history: exploratory 2025/26 comparisons

These five earlier experiments share 2,090 training rows (2021/22-2024/25) and 504 2025/26 evaluation rows. The first four use four numerical inputs; the last adds position. Their selection procedures differ, and repeated inspection means 2025/26 is exploratory rather than an untouched final benchmark.

| Experiment | MAE EUR | RMSE EUR | R2 |
|---|---:|---:|---:|
| linear_regression | 11,090,195.65 | 16,832,743.42 | 0.452857243619 |
| ridge | 11,105,366.51 | 16,933,828.73 | 0.446266022553 |
| random_forest | 10,135,335.82 | 16,081,107.85 | 0.500629623030 |
| xgboost | 10,090,465.83 | 15,947,555.47 | 0.508889646727 |
| xgboost_with_position | 9,993,665.91 | 15,781,526.95 | 0.519062225198 |

Linear Regression established the interpretable baseline. Ridge did not improve it; Random Forest improved all three aggregate metrics; four-feature XGBoost improved modestly on Random Forest. Position then improved aggregate scores, prompting a multi-season check. These single-season numbers must not be conflated with pooled backtest scores below.

## Accepted temporal out-of-fold evaluation

Each fold independently fits preprocessing and a fresh model using earlier seasons, then predicts the next season:

| Training seasons | Evaluation season | Train N | Evaluation N |
|---|---|---:|---:|
| 2021/22 | 2022/23 | 491 | 522 |
| 2021/22-2022/23 | 2023/24 | 1,013 | 534 |
| 2021/22-2023/24 | 2024/25 | 1,547 | 543 |
| 2021/22-2024/25 | 2025/26 | 2,090 | 504 |

Pooled over **2,103 out-of-fold predictions**:

| Metric | Temporal OOF result |
|---|---:|
| MAE | EUR 9,677,493.908572 |
| RMSE | EUR 15,046,414.971176 |
| R2 | 0.525160448535 |
| Median absolute error | EUR 5,881,224.00 |

Position improved MAE, RMSE and R2 in all four folds compared with four-feature XGBoost. This is consistent directional evidence, not a significance test. MAE summarizes mean absolute error; RMSE emphasizes large errors; pooled R2 compares squared errors with predicting the pooled target mean. None is a confidence interval for an individual prediction. Large errors remain: position-model pooled worst absolute error was EUR 111,807,272.

Frozen hyperparameters and 63 rounds were originally selected using 2024/25. Consequently, the retrospective folds have chronological row fitting but are not a fully nested historical model-selection simulation. Folds share training observations and players can recur. See [TEMPORAL_BACKTESTING.md](TEMPORAL_BACKTESTING.md).

## Rejected rates

goals_per_90 and assists_per_90 were tested, with raw totals retained, then rejected for V1. MAE worsened in all four folds; pooled MAE rose to EUR 9,749,592.38, RMSE to EUR 15,060,944.71, R2 fell to 0.524242937384, and median absolute error rose to EUR 5,988,754. All experiment artifacts are retained. This is useful selection evidence, not discarded work. Goal contributions per 90 was not added.

## Final-fit descriptive gain importance

These values describe the all-data production candidate, not the fold models. Gain indicates model split usefulness, not causation or percentage of market value explained.

| Transformed feature | Normalized gain |
|---|---:|
| goals | 0.284789085388 |
| assists | 0.198720484972 |
| age | 0.138285323977 |
| minutes | 0.080454364419 |
| position_AM | 0.055890485644 |
| position_ST | 0.044252108783 |
| position_DM | 0.038638647646 |
| position_W | 0.033551309258 |
| position_FB | 0.032708995044 |
| position_CM | 0.032266460359 |
| position_CB | 0.028736725450 |
| position_UNKNOWN | 0.023116134107 |
| position_GK | 0.008589865640 |

Summed position-family importance: **0.297750731930**. The 13 rows above list the complete transformed feature set.

## Inference checks and reproducibility

The requested hypothetical ST example (age 24, 3,000 minutes, 15 goals, 8 assists) returns EUR 82,459,040. Batch smoke inputs additionally returned EUR 27,531,842 for age 27, 2,800 minutes, 1 goal, 1 assist, CB; and EUR 19,211,188 for age 22, 900 minutes, 2 goals, 3 assists, an unseen position string mapped to UNKNOWN. These are raw smoke outputs, not evaluation results.

Negative outputs are possible and are not clipped. A sanity pass over the 2,594 input rows found one negative (minimum EUR -102,108.9375); this is an output-range check, not training performance. A 64-profile hypothetical grid spanning ages 18/24/32/38, GK/CB/CM/ST, and four minutes/production profiles also produced one negative (minimum EUR -170,012.28125). Future display policy must be explicit rather than silently altering the ML output.

Two all-data fits were run in separate output locations. Native booster states and smoke predictions matched exactly. Joblib file bytes differed despite equivalent model state, so hashes identify each serialized artifact rather than mathematical equivalence. Loading verifies the hash for the chosen artifact. Prior experiments, evaluation evidence and dataset hashes remained unchanged.

## Appropriate use

Educational ML work, football analytics exploration, hypothetical estimates, comparison views and a simulator interface. The artifact is a production candidate for those uses, not proof of operational reliability.

## Limitations and inappropriate use

Market value depends on information outside four numerical variables and one broad position: club strength, contract length, injury history, nationality/homegrown status, international performance, transfer demand, expected goals and advanced event data are absent. Snapshot positions may omit historical changes or multiple roles. Rates were rejected rather than smuggled into inference. Superstar extrapolation is limited and high individual errors occur. Data and evaluation cover the Premier League only; performance elsewhere is unverified.

Repeated historical experimentation makes evaluation exploratory. Missing-target selection and incomplete valuation coverage may bias the sample. The model must not be treated as an authoritative transfer valuation or used for professional financial decisions, contractual negotiations, replacement of human scouting expertise, or claims about objective true player value. No confidence scores or intervals are supplied.

## Artifacts and maintenance

Artifacts: ml/models/playerworth_v1.joblib, playerworth_v1_metadata.json, playerworth_v1_feature_importance.json and current_model.json. The pointer uses relative filenames. Metadata distinguishes deployment_training_rows=2594 from evaluation.pooled.rows=2103 and has final_fit_test_metrics=null. It records versions, provenance, hashes, configuration, limitations and the inherited OOF evidence.

```powershell
.venv\Scripts\python.exe -m ml.freeze_v1 --output-dir <fresh-directory>
.venv\Scripts\python.exe -m ml.inference --age 24 --minutes 3000 --goals 15 --assists 8 --position ST
```

Existing V1 outputs are protected from overwrite. No API, database or frontend was created, and Session 10 has not begun.
