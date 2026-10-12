# Session 7 - Position feature experiment

The controlled experiment adds only normalized position to age, minutes, goals and assists. The same 2,594 player-season rows, untransformed market_value_eur target, 2,090 training rows (2021/22-2024/25) and 504 test rows (2025/26) are retained. The source CSV is unchanged. No secondary tuning was performed.

## Why position and how it enters the model

A goal can carry different information for a centre-back and striker. Position lets the trees distinguish broad roles instead of interpreting production identically for every role. This is a predictive hypothesis, not a causal claim.

Position is categorical: ST, CB and GK have no numerical rank. The pipeline passes age/minutes/goals/assists through unchanged and applies a ColumnTransformer categorical branch: normalization followed by OneHotEncoder(handle_unknown="ignore", sparse_output=False). For example, ST becomes position_ST=1 with position_CB=0 and position_GK=0, alongside the other zero indicators. No StandardScaler or arbitrary ordinal codes are used.

The encoder learns categories from training rows only. Missing, blank and unmapped labels become UNKNOWN inside the saved pipeline. If inference contains a recognized category absent during fitting, handle_unknown="ignore" represents it with all-zero indicators. UNKNOWN is learned in this real training cohort. The normalization helper lives in an importable preprocessing module so serialization works across CLI and imported Python usage.

## Actual position counts

| Position | Overall | Training | Test |
|---|---:|---:|---:|
| AM | 181 | 143 | 38 |
| CB | 495 | 404 | 91 |
| CM | 326 | 268 | 58 |
| DM | 228 | 185 | 43 |
| FB | 427 | 341 | 86 |
| GK | 200 | 160 | 40 |
| ST | 324 | 257 | 67 |
| UNKNOWN | 26 | 24 | 2 |
| W | 387 | 308 | 79 |

All 26 missing positions are retained as UNKNOWN (24 training, 2 test). There are no other unmapped nonempty labels in this dataset. No rows were discarded.

## Frozen model settings

XGBoost 3.4.1, reg:squarederror, max_depth=4, learning_rate=0.1, min_child_weight=5, subsample=0.8, colsample_bytree=0.8, 63 boosting rounds, random_state=42, CPU hist, n_jobs=1. There is no early stopping, validation search or test-informed adjustment in this session. The estimator is constructed through the unchanged Session 6 helper.

The encoder expands five source features to 13 numerical columns: four numerical features plus nine position indicators. Holding colsample_bytree=0.8 fixed changes how many transformed columns are sampled per tree. This is part of adding the encoded feature; the result is not a causal isolation of each individual position indicator.

## Held-out results

| Model | MAE EUR | RMSE EUR | R2 |
|---|---:|---:|---:|
| Frozen four-feature XGBoost | 10,090,465.831721 | 15,947,555.471390 | 0.508889646727 |
| XGBoost with position | 9,993,665.908482 | 15,781,526.954306 | 0.519062225198 |

MAE improves EUR 96,799.923239 (0.959321%); RMSE improves EUR 166,028.517084; R2 increases 0.010172578471. Position modestly improves all three held-out point estimates under this configuration. This is not a statistical significance claim or proof of historical deployability.

## Errors by test position

| Position | N | Old MAE EUR | New MAE EUR | New median AE EUR | New RMSE EUR |
|---|---:|---:|---:|---:|---:|
| AM | 38 | 14,736,257.78 | 14,279,355.17 | 9,382,802.00 | 20,218,403.30 |
| CB | 91 | 9,911,519.36 | 9,623,003.94 | 5,594,776.00 | 15,139,333.04 |
| CM | 58 | 9,410,474.64 | 9,581,442.41 | 5,529,760.00 | 15,935,719.83 |
| DM | 43 | 12,247,922.66 | 12,659,753.57 | 8,226,449.00 | 18,038,670.41 |
| FB | 86 | 8,390,897.54 | 8,098,441.33 | 5,336,528.00 | 11,432,672.23 |
| GK | 40 | 4,661,616.19 | 4,524,646.11 | 2,839,163.00 | 6,535,063.86 |
| ST | 67 | 11,981,481.97 | 11,804,467.57 | 5,179,191.00 | 20,346,367.49 |
| W | 79 | 10,417,343.25 | 10,648,846.53 | 6,483,624.00 | 15,780,531.86 |
| UNKNOWN | 2 | 8,694,637.00 | 4,397,849.00 | 4,397,849.00 | not reported |

MAE improves for AM, CB, FB, GK and ST, and worsens for CM, DM and W. UNKNOWN improves descriptively but has only two observations: no robust conclusion follows. RMSE is withheld for groups with fewer than five rows; five is a reporting threshold, not a statistical reliability guarantee. Different error summaries can disagree: GK and ST MAE improve while their RMSE worsens.

## Transformed gain importance

| Transformed feature | Normalized gain |
|---|---:|
| goals | 0.306600391865 |
| assists | 0.192611202598 |
| age | 0.133048176765 |
| minutes | 0.077074706554 |
| position_AM | 0.070094674826 |
| position_CM | 0.041950855404 |
| position_DM | 0.038158409297 |
| position_CB | 0.035668998957 |
| position_W | 0.034036628902 |
| position_ST | 0.025670614094 |
| position_FB | 0.016723997891 |
| position_UNKNOWN | 0.016205007210 |
| position_GK | 0.012156290002 |

Summed position-family importance: **0.290665476583** (29.066548%). This is the sum of normalized average-gain importances for position_* columns. It describes model split usefulness, not causal effect or a percentage of market value explained. Splitting a feature into indicators affects importance allocation.

## Named players: post-evaluation analysis

| Player | Position | Actual EUR | Old prediction EUR | New prediction EUR | Old AE EUR | New AE EUR |
|---|---|---:|---:|---:|---:|---:|
| Declan Rice | CM | 120,000,000.00 | 46,780,152.00 | 45,636,568.00 | 73,219,848.00 | 74,363,432.00 |
| Erling Haaland | ST | 200,000,000.00 | 118,101,656.00 | 111,439,696.00 | 81,898,344.00 | 88,560,304.00 |
| William Saliba | CB | 100,000,000.00 | 27,099,846.00 | 27,538,044.00 | 72,900,154.00 | 72,461,956.00 |
| Cole Palmer | AM | 100,000,000.00 | 34,088,748.00 | 41,064,324.00 | 65,911,252.00 | 58,935,676.00 |
| Moisés Caicedo | DM | 100,000,000.00 | 31,037,976.00 | 39,329,908.00 | 68,962,024.00 | 60,670,092.00 |

The actual normalized categories are ST for Haaland, CB for Saliba, CM for Rice, DM for Caicedo and AM for Palmer. Saliba, Caicedo and Palmer improve; Haaland and Rice worsen. No parameters were tuned to these players. Residual remains actual minus predicted.

## Range and errors

| Quantity | Four features | With position |
|---|---:|---:|
| negative_prediction_count | 0.000000 | 0.000000 |
| minimum_prediction_eur | 525,205.562500 | 822,690.125000 |
| maximum_prediction_eur | 125,509,216.000000 | 133,754,040.000000 |
| median_absolute_error_eur | 6,089,521.000000 | 5,817,428.250000 |
| worst_absolute_error_eur | 81,898,344.000000 | 88,560,304.000000 |

Predictions are not clipped. The worst absolute error increases despite better aggregate metrics; Haaland remains substantially underpredicted.

## Files and commands

```powershell
.venv\Scripts\python.exe -m ml.xgboost_position train
.venv\Scripts\python.exe -m ml.xgboost_position evaluate
```

Training refuses to overwrite its artifacts. Use --output-dir with a fresh directory to reproduce, and --baseline-dir to specify frozen artifacts (default ml/models). The five new files use the xgboost_position prefix: .joblib, _metadata.json, _feature_importance.json, _test_predictions.csv and _analysis.json. Preprocessing and estimator are serialized together. Metadata records counts, features, model settings, versions, provenance and hashes.

model_metrics.json keeps the stable xgboost model identifier and original metrics, adding comparison_name=xgboost_4_features. The separate xgboost_with_position entry identifies the experiment. Previous model files are unchanged. The CSV cohort, numerical features and target values are checked against the old prediction artifact. Repeated training reproduces metrics, prediction CSV bytes and native booster bytes; reload predictions reproduce the saved metrics.

## Limitations

**Position is undated Transfermarkt snapshot metadata. Historical validity has not been independently verified.** Past positional changes may be lost, players can play multiple positions, and only one broad category per row is modeled. This experiment is explicitly allowed despite that limitation; the improvement does not prove a leakage-free historical position feature. Richer performance statistics remain unavailable, club context is omitted, and target values incorporate external market information. The two UNKNOWN test rows are too few for general claims. The same holdout has been reused across experiments, so conclusions are exploratory. No next feature experiment, application or database work was performed.
