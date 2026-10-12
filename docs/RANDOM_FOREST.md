# Session 5 - PlayerWorth Random Forest Regression

This experiment keeps the corrected 2,594-row dataset, age/minutes/goals/assists inputs, untransformed market_value_eur target, and temporal test split unchanged. No rows were dropped. Linear Regression and Ridge artifacts are frozen. Session numbering follows the current request; no database work is included.

## How the fitted forest works

A decision tree asks threshold questions about inputs and routes a player to a leaf. An actual root split from this fitted forest's first tree is `assists <= 4.5`. Later branches can ask about age, goals, minutes or assists. Leaves predict the average training valuation among their bootstrap samples. This threshold is extracted from the saved model, not an invented football rule.

The Random Forest averages 300 trees trained on bootstrap samples of training rows. Random feature subsets make trees different. Branches allow the relationship between goals and value to depend on age, or minutes to matter differently for younger and older players, without adding polynomial features. These are possible interactions, not causal findings.

No StandardScaler is used. Tree thresholds divide ordered feature values; expressing minutes in different units does not change their order. Ridge penalizes coefficient magnitudes, so its scaling issue does not apply here. Missing or invalid selected inputs fail shared validation rather than being silently dropped or imputed.

## Selection and leakage protection

All 24 candidates fitted 1,547 rows from 2021/22-2023/24 and validated on 543 rows from 2024/25. Selection accepts only the four outer-training seasons and rejects 2025/26. Lowest validation MAE wins; scores within EUR 0.01 are treated as equal, then RMSE uses the same tolerance, then shallower trees and larger leaves win. A stable max_features ordering resolves remaining ties. The 2025/26 holdout did not select parameters.

Every candidate uses n_estimators=300, random_state=42 and n_jobs=1. The last setting fixes prediction accumulation order for reproducibility. The exact requested grid is depth {4,8,12,None}, min_samples_leaf {1,3,8}, max_features {1.0,sqrt}.

| Depth | Minimum leaf | Max features | Validation MAE EUR | Validation RMSE EUR | R2 |
|---|---:|---|---:|---:|---:|
| 4 | 1 | 1.0 | 10,079,717.547576 | 16,363,459.767873 | 0.428429475027 |
| 4 | 1 | sqrt | 10,170,696.265780 | 16,387,596.144975 | 0.426742079290 |
| 4 | 3 | 1.0 | 10,021,385.344972 | 16,110,540.472927 | 0.445961711138 |
| 4 | 3 | sqrt | 10,153,666.106363 | 16,242,854.058302 | 0.436823864806 |
| 4 | 8 | 1.0 | 10,067,702.009632 | 16,199,299.402721 | 0.439840090373 |
| 4 | 8 | sqrt | 10,170,105.681985 | 16,358,524.300152 | 0.428774211714 |
| 8 | 1 | 1.0 | 9,949,621.527220 | 16,007,162.787517 | 0.453049174784 |
| 8 | 1 | sqrt | 9,817,247.792037 | 15,849,201.472363 | 0.463790713751 |
| 8 | 3 | 1.0 | 9,864,643.847299 | 15,832,891.413750 | 0.464893747863 |
| 8 | 3 | sqrt | 9,771,736.644025 | 15,732,206.605299 | 0.471677822998 |
| 8 | 8 | 1.0 | 9,824,936.659151 | 15,883,589.227183 | 0.461461380386 |
| 8 | 8 | sqrt | 9,782,097.998257 | 15,900,780.202224 | 0.460295017563 |
| 12 | 1 | 1.0 | 10,350,360.062381 | 16,253,918.543921 | 0.436056342478 |
| 12 | 1 | sqrt | 10,211,399.115600 | 16,166,836.786770 | 0.442082907840 |
| 12 | 3 | 1.0 | 10,085,623.229805 | 16,001,609.808555 | 0.453428589881 |
| 12 | 3 | sqrt | 10,021,330.721276 | 15,984,596.689962 | 0.454590215616 |
| 12 | 8 | 1.0 | 9,882,699.182098 | 15,923,295.341455 | 0.458765515763 |
| 12 | 8 | sqrt | 9,827,606.701231 | 15,985,479.429110 | 0.454529974138 |
| None | 1 | 1.0 | 10,469,383.098746 | 16,291,406.265336 | 0.433452005287 |
| None | 1 | sqrt | 10,427,708.288998 | 16,274,736.008130 | 0.434610857822 |
| None | 3 | 1.0 | 10,121,855.793805 | 16,028,770.835241 | 0.451571521735 |
| None | 3 | sqrt | 10,056,563.027469 | 15,986,778.352776 | 0.454441324596 |
| None | 8 | 1.0 | 9,883,343.279036 | 15,922,424.100850 | 0.458824741262 |
| None | 8 | sqrt | 9,845,591.475202 | 15,993,824.928535 | 0.453960281113 |

**Selected: 300 trees, max_depth=8, min_samples_leaf=3, max_features="sqrt".** n_estimators controls the number of averaged trees; max_depth caps branch depth; min_samples_leaf requires at least three samples in each leaf; sqrt considers two of the four features at each split (the splitter may inspect more to find a valid partition). These constraints limit tree complexity.

The selected pipeline was refitted on all 2,090 rows from 2021/22-2024/25, then evaluated on the same 504 rows from 2025/26. No test-based retuning occurred. Validation MAE was EUR 9,771,736.644025, RMSE EUR 15,732,206.605299, R2 0.471677822998.

## Actual held-out comparison

| Model | MAE EUR | RMSE EUR | R2 |
|---|---:|---:|---:|
| linear_regression | 11,090,195.645218 | 16,832,743.420461 | 0.452857243619 |
| ridge | 11,105,366.505469 | 16,933,828.732498 | 0.446266022553 |
| random_forest | 10,135,335.817899 | 16,081,107.851481 | 0.500629623030 |

Random Forest improved all three held-out point estimates. This supports improvement on this particular season, not universal superiority or statistical significance. It is not designated a production model.

Against linear_regression: MAE decreased EUR 954,859.827319 (8.609946%); RMSE decreased EUR 751,635.568980; R2 increased 0.047772379410.
Against ridge: MAE decreased EUR 970,030.687570 (8.734792%); RMSE decreased EUR 852,720.881017; R2 increased 0.054363600477.

## Feature importance

| Feature | Impurity importance |
|---|---:|
| goals | 0.330361199228 |
| minutes | 0.232956730735 |
| assists | 0.220433101591 |
| age | 0.216248968446 |

These normalized impurity-based importances summarize reductions in squared-error impurity from training splits, averaged across trees. Goals contribute most in this fitted forest. They do not express EUR per goal or prove causation, and they are not comparable to linear coefficients. Correlated predictors can share or obscure importance, and features with more possible thresholds can be favored. Optional permutation importance was not added.

## Prediction range and errors

| Quantity | EUR |
|---|---:|
| minimum_prediction_eur | 1,222,417.337220 |
| maximum_prediction_eur | 101,107,030.214015 |
| minimum_training_target_eur | 75,000.000000 |
| maximum_training_target_eur | 180,000,000.000000 |
| worst_absolute_error_eur | 98,892,969.785985 |
| median_absolute_error_eur | 6,034,822.306469 |

Negative predictions: **0**, versus 20 for Linear Regression and 16 for Ridge. No clipping was applied. With nonnegative training targets, averages of leaf target means remain nonnegative. This forest cannot extrapolate above the EUR 180M training maximum or below its EUR 75,000 minimum; its actual prediction range is narrower still. Haaland has an observed EUR 200M target, outside that training range, and is predicted at about EUR 101.107M. Averaging and minimum leaf constraints also smooth rare superstar observations within the training range.

The worst error fell from EUR 109.902M (Linear Regression) and EUR 112.012M (Ridge) to EUR 98.893M, but remains substantial. Residual = actual - predicted; positive means model underprediction. These errors do not establish objective player overvaluation or undervaluation.

### Five closest predictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Caoimhín Kelleher | 28,000,000.00 | 28,060,895.04 | -60,895.04 |
| Jean-Clair Todibo | 22,000,000.00 | 21,930,964.74 | 69,035.26 |
| Ethan Pinnock | 3,000,000.00 | 2,923,719.28 | 76,280.72 |
| Vitaliy Mykolenko | 25,000,000.00 | 25,119,371.11 | -119,371.11 |
| Mats Wieffer | 25,000,000.00 | 24,873,047.28 | 126,952.72 |

### Five largest underpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Erling Haaland | 200,000,000.00 | 101,107,030.21 | 98,892,969.79 |
| William Saliba | 100,000,000.00 | 25,635,060.84 | 74,364,939.16 |
| Declan Rice | 120,000,000.00 | 47,779,696.05 | 72,220,303.95 |
| Cole Palmer | 100,000,000.00 | 31,546,042.28 | 68,453,957.72 |
| Moisés Caicedo | 100,000,000.00 | 32,519,069.26 | 67,480,930.74 |

### Five largest overpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Jarrod Bowen | 30,000,000.00 | 63,435,862.95 | -33,435,862.95 |
| Santiago Bueno | 10,000,000.00 | 33,819,979.78 | -23,819,979.78 |
| Jaidon Anthony | 20,000,000.00 | 42,837,585.34 | -22,837,585.34 |
| Igor Thiago | 65,000,000.00 | 87,757,900.71 | -22,757,900.71 |
| Brenden Aaronson | 22,000,000.00 | 43,532,435.29 | -21,532,435.29 |

## Commands, artifacts and verification

```powershell
.venv\Scripts\python.exe -m ml.random_forest train
.venv\Scripts\python.exe -m ml.random_forest evaluate
```

Training refuses to overwrite Random Forest artifacts. For reproduction use --output-dir with a fresh directory; --baseline-dir defaults to ml/models. The module reuses baseline feature validation, temporal split, metrics and prediction analysis while preserving earlier model code and source hashes. Evaluation reloads the saved model without fitting.

Created artifacts: random_forest.joblib, random_forest_metadata.json, random_forest_feature_importance.json, random_forest_test_predictions.csv, random_forest_analysis.json. model_metrics.json retains the original two entries and adds only the real forest result. Metadata includes every candidate, selection policy, final parameters, provenance, dataset/hash, code/artifact hashes, versions and timestamp.

Dataset SHA256: `1330a7a7190782cb4b231e7cc796626f4106be30dbaf7269dbbf211848e7c514`. Both previous models and their artifacts remained byte-identical, and test identities, features and targets matched both earlier prediction files. Repeated real searches reproduced candidate results, selected parameters, all learned tree arrays, final metrics and prediction CSV bytes exactly. Joblib file bytes differed between real repeated fits despite identical fitted tree arrays; model-file hashes identify each saved file, not mathematical reproducibility. Each saved model is independently hash-checked on reload.

## Remaining limitations

Only four features are used. Position and club strength remain omitted, richer statistics are unavailable, and valuations contain external information beyond match performance. Trees cannot extrapolate beyond the training target range. One validation season and a small grid constrain conclusions. Players recur across seasons, so this tests an unseen season rather than exclusively unseen people. Repeated comparison on the same holdout should not motivate tuning against it. Source limitations remain, including incomplete coverage of the full 2025/26 post-season valuation window and selection bias from missing targets. No XGBoost, new features, frontend, backend or database work was performed.
