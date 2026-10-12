# Session 7.5 - Temporal backtesting

PlayerWorth now evaluates the frozen four-feature XGBoost and position-aware XGBoost across four expanding training windows. No features, hyperparameters, targets, source rows or saved models were changed.

## Why the earlier holdout is exploratory

2025/26 has been inspected repeatedly while comparing algorithms and features. Even without fitting directly on its rows, those observations can indirectly influence subsequent model choices. The existing results are not invalid: they remain exploratory held-out-season results. We no longer describe 2025/26 as a completely untouched final test set.

## Past seasons predict the next season

Each fold starts a fresh model, fits only earlier seasons, and predicts the next season. Training expands while test seasons advance. This matches the intended use of completed historical seasons to estimate values in a later season more closely than shuffling observations across time.

| Fold | Train seasons | Train rows | Test season | Test rows |
|---:|---|---:|---|---:|
| 1 | 2021/22 | 491 | 2022/23 | 522 |
| 2 | 2021/22, 2022/23 | 1013 | 2023/24 | 534 |
| 3 | 2021/22, 2022/23, 2023/24 | 1547 | 2024/25 | 543 |
| 4 | 2021/22, 2022/23, 2023/24, 2024/25 | 2090 | 2025/26 | 504 |

Both definitions use reg:squarederror, depth 4, learning rate 0.1, min_child_weight 5, subsample 0.8, colsample_bytree 0.8, 63 rounds and seed 42, with CPU hist and one worker. No early stopping or hyperparameter search occurs.

The numerical model uses age, minutes, goals and assists. The position model adds only normalized position. Its fresh ColumnTransformer and OneHotEncoder are fitted separately within each fold. Missing/unmapped labels become UNKNOWN. Valid categories unseen during fitting use handle_unknown="ignore". Encoder categories for each training fold are saved in the summary as an audit.

## Per-fold results

| Model | Test season | MAE EUR | RMSE EUR | R2 | Median AE EUR | Negative predictions | Worst AE EUR |
|---|---|---:|---:|---:|---:|---:|---:|
| xgboost_4_features | 2022/23 | 9,374,251.940793 | 14,495,701.325516 | 0.482528238403 | 5,714,201.500000 | 8 | 101,498,736.000000 |
| xgboost_with_position | 2022/23 | 8,958,891.885028 | 14,099,996.312288 | 0.510394611017 | 5,667,744.000000 | 2 | 111,807,272.000000 |
| xgboost_4_features | 2023/24 | 10,269,196.889045 | 15,213,675.871917 | 0.540048708880 | 6,226,749.000000 | 0 | 86,633,640.000000 |
| xgboost_with_position | 2023/24 | 10,244,197.856259 | 14,994,873.150020 | 0.553183588885 | 6,264,902.000000 | 0 | 87,179,304.000000 |
| xgboost_4_features | 2024/25 | 9,562,915.187615 | 15,445,367.562564 | 0.490767568749 | 5,835,709.500000 | 0 | 106,522,460.000000 |
| xgboost_with_position | 2024/25 | 9,517,530.115331 | 15,277,463.308783 | 0.501778967447 | 5,915,594.000000 | 0 | 111,559,576.000000 |
| xgboost_4_features | 2025/26 | 10,090,465.831721 | 15,947,555.471390 | 0.508889646727 | 6,089,521.000000 | 0 | 81,898,344.000000 |
| xgboost_with_position | 2025/26 | 9,993,665.908482 | 15,781,526.954306 | 0.519062225198 | 5,817,428.250000 | 0 | 88,560,304.000000 |

## Position comparison

Differences are position minus four features. Negative MAE/RMSE differences favor position; positive R2 differences favor position.

| Test season | MAE difference EUR | MAE difference % | RMSE difference EUR | R2 difference |
|---|---:|---:|---:|---:|
| 2022/23 | -415,360.055765 | -4.430861 | -395,705.013227 | 0.027866372613 |
| 2023/24 | -24,999.032786 | -0.243437 | -218,802.721897 | 0.013134880005 |
| 2024/25 | -45,385.072284 | -0.474595 | -167,904.253781 | 0.011011398698 |
| 2025/26 | -96,799.923239 | -0.959321 | -166,028.517084 | 0.010172578471 |

Position improves MAE in **4/4** seasons, worsens MAE in **0/4**, improves RMSE in **4/4**, and improves R2 in **4/4**. Thus the direction of improvement is consistent across these retrospective folds, not just 2025/26. Its magnitude varies considerably; no significance test was performed.

## Equal-weight fold averages

Each season receives equal weight here, regardless of its test row count. Mean fold median AE averages four separate medians; it is not the median over all prediction errors.

| Model | Mean MAE EUR | Median fold MAE EUR | Mean RMSE EUR | Mean R2 | Mean fold median AE EUR |
|---|---:|---:|---:|---:|---:|
| xgboost_4_features | 9,824,207.462293 | 9,826,690.509668 | 15,275,575.057847 | 0.505558540690 | 5,966,545.250000 |
| xgboost_with_position | 9,678,571.441275 | 9,755,598.011907 | 15,038,464.931350 | 0.521104848137 | 5,916,417.062500 |

## Pooled out-of-fold results

Each model has 2,103 out-of-fold player-season predictions across 2022/23-2025/26; both models together produce 4,206 CSV rows. The first season is training-only. Each eligible player-season is tested once per model. These metrics are recalculated from pooled actual/predicted values, not averaged from fold scores. Pooled R2 uses the pooled target mean.

| Model | N | MAE EUR | RMSE EUR | R2 | Median AE EUR |
|---|---:|---:|---:|---:|---:|
| xgboost_4_features | 2103 | 9,821,858.477369 | 15,279,924.275166 | 0.510307762735 | 5,912,180.000000 |
| xgboost_with_position | 2103 | 9,677,493.908572 | 15,046,414.971176 | 0.525160448535 | 5,881,224.000000 |

Across pooled predictions, negative predictions fall from 8 to 2, but worst absolute error increases from EUR 106,522,460 to EUR 111,807,272. No predictions are clipped. Better average performance does not imply every player improves.

## Reusable implementation and outputs

`ml/temporal_backtest.py` owns fold construction, fresh model fits, common metric aggregation and output generation. It reuses the existing experiment builders and evaluation helpers without changing their code. The declared season set is validated; unexpected/missing seasons fail rather than being silently filtered. IDs and names are audit columns only.

```powershell
.venv\Scripts\python.exe -m ml.temporal_backtest
```

For a repeat run use --output-dir with a fresh directory. Existing evaluation files are protected from overwrite. The default ml/evaluation area contains temporal_backtest_summary.json, temporal_backtest_predictions.csv and temporal_backtest_fold_metrics.csv. No saved model or model_metrics.json is overwritten. Residual remains actual minus predicted; train_seasons uses a pipe-separated list in CSV. Position is blank for the four-feature model because it is not used there.

The summary records dataset/code hashes, versions, fixed settings, fold counts, encoder categories, per-fold comparisons, aggregates, pooled results and hashes of all existing top-level model artifacts. Hashes are checked after fitting. Repeating the real run reproduced metrics and both output CSV hashes exactly. Synthetic tests cover chronology, eligible-season coverage, separate preprocessing, UNKNOWN, unseen categories, prediction lengths/finiteness, pooled calculations, future-target isolation, determinism and preservation of prior files.

## Limits of this retrospective assessment

**The frozen settings and 63 rounds were originally selected using 2024/25.** Reusing them for earlier folds means configuration selection itself was informed by a later season. Row fitting and preprocessing are chronological, but this is not a fully nested, historically independent selection simulation. This limitation is retained to honor the requested fixed comparison; no retuning is performed.

Position remains historically unverified snapshot metadata. Players recur, training windows overlap, and only four test seasons are available, so folds are not independent samples. Dataset coverage and missing-target selection limitations remain. Reusing these same seasons for future experimentation can also create selection pressure. No significance or causal claim follows from four wins.

## Future feature protocol

All future feature experiments must run this temporal backtesting framework before acceptance into the preferred model. Predeclare the candidate change, keep comparable cohorts, fit preprocessing only inside each training fold, and inspect per-season as well as pooled metrics and errors. Do not accept a feature solely because it improves 2025/26. If future experiments tune parameters, that selection must use only data earlier than each outer test season through inner temporal validation; it must not consult outer-fold labels. Retain a genuinely new future season for prospective confirmation when available. No next feature experiment was begun.
