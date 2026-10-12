# Session 8 - Per-90 scoring rates

**Decision: do not accept these rate features into the preferred model.** MAE worsens in all four seasons, and pooled MAE, RMSE, R2 and median absolute error all worsen. Retain the accepted position model. This conclusion applies to this frozen experiment, not every possible use of rates.

## Intuition and exact inputs

Conceptually stat_per_90 = stat / minutes * 90. Two hypothetical players with 10 goals in 3,000 and 1,500 minutes have 0.30 and 0.60 goals per 90 respectively. Equal totals can conceal different scoring rates. This does not imply causation or guarantee better valuation predictions. Minutes remains an input because it carries playing-time, selection and availability information.

The baseline uses age, minutes, goals, assists, position. The experiment adds only existing goals_per_90 and assists_per_90 columns. Goal contributions per 90 is excluded. Modeling never recomputes rates, changes the CSV, drops rows, scales inputs, clips predictions or tunes hyperparameters.

## Real source inspection and missingness

| Feature | Dtype | Missing | Minimum | Median | Mean | Maximum |
|---|---|---:|---:|---:|---:|---:|
| goals_per_90 | float64 | 0 | 0.000000 | 0.037445 | 0.117588 | 2.812500 |
| assists_per_90 | float64 | 0 | 0.000000 | 0.038528 | 0.095142 | 5.625000 |

There are zero zero-minute rows and zero infinities. George Earthy (2023/24) has 2.8125 goals per 90 from 32 minutes. The maximum assists rate is 5.625 per 90; such extremes reflect small denominators and are retained. No winsorization or minimum-minutes threshold is introduced.

If rates are missing, NaN passes through the numerical branch to native XGBoost missing-value handling. No imputation is fitted. Infinite or negative rates fail validation. The existing data pipeline leaves zero-minute rates missing; modeling consumes the supplied rates without dividing again. Position normalization and UNKNOWN handling remain unchanged, with a fresh encoder trained inside every fold.

## Frozen experiment and temporal evaluation

XGBoost 3.4.1 uses depth 4, learning rate 0.1, child weight 5, subsample 0.8, colsample_bytree 0.8, 63 rounds, seed 42, squared-error objective, CPU hist and one worker. The same earlier-season folds and entire cohort are used for both models. The backtester now accepts a pair of model definitions; its previous default behavior remains unchanged. Baseline predictions were checked against the accepted Session 7.5 artifact.

| Model | Test season | Train N | Test N | MAE EUR | RMSE EUR | R2 | Median AE EUR | Negative N | Worst AE EUR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| xgboost_with_position | 2022/23 | 491 | 522 | 8,958,891.89 | 14,099,996.31 | 0.510394611017 | 5,667,744.00 | 2 | 111,807,272.00 |
| xgboost_position_per90 | 2022/23 | 491 | 522 | 9,057,168.82 | 14,327,952.66 | 0.494435620596 | 5,372,136.75 | 1 | 114,128,416.00 |
| xgboost_with_position | 2023/24 | 1013 | 534 | 10,244,197.86 | 14,994,873.15 | 0.553183588885 | 6,264,902.00 | 0 | 87,179,304.00 |
| xgboost_position_per90 | 2023/24 | 1013 | 534 | 10,283,704.82 | 14,951,197.49 | 0.555782687893 | 6,628,986.00 | 0 | 85,388,048.00 |
| xgboost_with_position | 2024/25 | 1547 | 543 | 9,517,530.12 | 15,277,463.31 | 0.501778967447 | 5,915,594.00 | 0 | 111,559,576.00 |
| xgboost_position_per90 | 2024/25 | 1547 | 543 | 9,623,018.03 | 15,393,657.48 | 0.494171614671 | 6,136,973.00 | 0 | 105,674,896.00 |
| xgboost_with_position | 2025/26 | 2090 | 504 | 9,993,665.91 | 15,781,526.95 | 0.519062225198 | 5,817,428.25 | 0 | 88,560,304.00 |
| xgboost_position_per90 | 2025/26 | 2090 | 504 | 10,037,209.31 | 15,547,229.09 | 0.533236548298 | 5,788,673.25 | 0 | 75,084,712.00 |

| Season | Per-90 minus baseline MAE EUR | Percentage difference |
|---|---:|---:|
| 2022/23 | 98,276.936512 | 1.096976% |
| 2023/24 | 39,506.960396 | 0.385652% |
| 2024/25 | 105,487.911602 | 1.108354% |
| 2025/26 | 43,543.406351 | 0.435710% |

MAE improves in 0 folds and worsens in 4. RMSE improves in 2; R2 improves in 2. Looking only at 2025/26 RMSE would give an incomplete picture.

## Pooled out-of-fold results

| Model | N | MAE EUR | RMSE EUR | R2 | Median AE EUR |
|---|---:|---:|---:|---:|---:|
| xgboost_with_position | 2103 | 9,677,493.908572 | 15,046,414.971176 | 0.525160448535 | 5,881,224.000000 |
| xgboost_position_per90 | 2103 | 9,749,592.382424 | 15,060,944.711893 | 0.524242937384 | 5,988,754.000000 |

Each model has 2,103 out-of-fold predictions; these metrics are computed from pooled errors, not averages of fold metrics. Equal-weight fold averages are also retained in the JSON. Pooled MAE rises EUR 72,098.47; worst error rises from EUR 111,807,272 to EUR 114,128,416. Negative predictions decrease from 2 to 1, without clipping.

## Pooled position effects

| Position | N | Baseline MAE EUR | Per-90 MAE EUR |
|---|---:|---:|---:|
| AM | 154 | 12,831,362.99 | 13,165,290.31 |
| CB | 394 | 9,543,243.01 | 9,381,605.05 |
| CM | 260 | 9,844,385.75 | 10,180,100.47 |
| DM | 187 | 11,364,893.38 | 11,800,671.97 |
| FB | 349 | 7,744,454.59 | 7,633,971.14 |
| GK | 160 | 4,861,042.33 | 4,828,440.47 |
| ST | 264 | 11,448,699.84 | 11,483,431.64 |
| W | 313 | 10,496,896.30 | 10,542,074.92 |
| UNKNOWN | 22 | 6,470,907.38 | 7,178,731.87 |

CB, FB and GK improve slightly. AM, CM, DM, ST, W and UNKNOWN worsen. The rates do not consistently help attacking roles. UNKNOWN has only 22 pooled player-seasons and should not be overinterpreted.

## Descriptive importance and redundancy

The final 2021/22-2024/25 fit is saved for descriptive analysis only, not promoted. Importance uses normalized average split gain, matching previous experiments.

| Transformed feature | Gain importance |
|---|---:|
| goals | 0.274509191513 |
| assists | 0.163623303175 |
| age | 0.115283504128 |
| minutes | 0.084457881749 |
| position_AM | 0.062096804380 |
| position_ST | 0.049683295190 |
| assists_per_90 | 0.046667419374 |
| position_W | 0.040689110756 |
| position_CM | 0.034754324704 |
| position_DM | 0.034352228045 |
| goals_per_90 | 0.033698607236 |
| position_CB | 0.026464909315 |
| position_UNKNOWN | 0.017329931259 |
| position_FB | 0.008691177703 |
| position_GK | 0.007698203437 |

Raw goals + assists: 0.438132494688.

Rate production: 0.080366026610.

Position indicators: 0.281759984791.

These sums are not percentages of market value explained and do not establish causation. Adding columns also changes feature subsampling under the same colsample_bytree setting.

| Training Pearson correlation | Value |
|---|---:|
| goals__goals_per_90 | 0.672207372184 |
| assists__assists_per_90 | 0.585829180240 |
| minutes__goals_per_90 | 0.080693680071 |
| minutes__assists_per_90 | 0.063154500905 |

Correlations use only 2021/22-2024/25, with pairwise complete observations. Totals and rates are mathematically related. Trees can use related features, but redundancy redistributes importance. No input was removed based on correlation.

## Named players after evaluation (2025/26)

| Player | Actual EUR | Baseline prediction EUR | Per-90 prediction EUR | Baseline AE EUR | Per-90 AE EUR |
|---|---:|---:|---:|---:|---:|
| Declan Rice | 120,000,000.00 | 45,636,568.00 | 49,516,320.00 | 74,363,432.00 | 70,483,680.00 |
| Erling Haaland | 200,000,000.00 | 111,439,696.00 | 124,915,288.00 | 88,560,304.00 | 75,084,712.00 |
| William Saliba | 100,000,000.00 | 27,538,044.00 | 27,782,696.00 | 72,461,956.00 | 72,217,304.00 |
| Cole Palmer | 100,000,000.00 | 41,064,324.00 | 40,654,956.00 | 58,935,676.00 | 59,345,044.00 |
| Moisés Caicedo | 100,000,000.00 | 39,329,908.00 | 40,215,008.00 | 60,670,092.00 | 59,784,992.00 |

largest_improvement: Igor Thiago, 2025/26, actual EUR 65,000,000.00; prediction changes from EUR 133,754,040.00 to EUR 114,395,232.00. Absolute error changes from EUR 68,754,040.00 to EUR 49,395,232.00.

largest_worsening: Ollie Watkins, 2024/25, actual EUR 40,000,000.00; prediction changes from EUR 57,689,040.00 to EUR 79,137,912.00. Absolute error changes from EUR 17,689,040.00 to EUR 39,137,912.00.

These examples did not influence training or model selection. Residual is actual minus predicted.

## Commands and artifacts

```powershell
.venv\Scripts\python.exe -m ml.per90_experiment
```

Use fresh --output-dir and --model-dir paths for a repeat; existing experiment artifacts are protected. The three ml/evaluation/per90_backtest_* files contain summary, fold metrics and predictions. The three ml/models/xgboost_position_per90 files contain the descriptive pipeline, metadata and transformed importance. Accepted model files and model_metrics.json remain unchanged. Dataset and prior artifacts are hash-checked. Repeat training reproduced pooled/fold metrics, output CSV hashes and native booster bytes.

## Limitations and decision

Low-minute rates are unstable; totals and rates are mathematically related; some roles have small samples; richer expected-goals/chance-creation measures are unavailable; market values include context beyond match production. Position remains snapshot metadata. Frozen settings were selected using 2024/25, so these are retrospective rather than nested selection results. Repeated holdout inspection and overlapping training windows limit certainty. No statistical significance claim is made.

Keep the position-only baseline preferred: all four MAEs and pooled metrics oppose accepting this feature family under the frozen settings. The descriptive per-90 model is retained only as an experiment. Session 9 has not begun.
