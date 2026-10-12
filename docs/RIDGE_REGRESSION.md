# Session 4 — PlayerWorth Ridge Regression

Ridge was tested on the unchanged 2,594-row dataset with age, minutes, goals and assists as inputs and market_value_eur as target. No rows were dropped. No features or target transforms were added. This is an experiment, not a production model.

## What Ridge changes

PlayerWorth still fits a linear equation. Ridge minimizes the sum of squared prediction errors plus alpha times the sum of squared coefficients. The intercept is not penalized. Penalizing large coefficients can help when features overlap (minutes, goals and assists can carry related information), coefficients are unstable, or variance is high. It does not guarantee better future-season predictions.

## Temporal validation and alpha

Each candidate fitted 1,547 rows from 2021/22–2023/24 and validated on 543 rows from 2024/25. Lowest validation MAE selected alpha; exact ties prefer smaller alpha. No 2025/26 observations entered this selection. Each candidate fitted its own scaler on its fitting rows only.

| Alpha | Validation MAE (EUR) | Validation RMSE (EUR) | Validation R² |
|---:|---:|---:|---:|
| 0.01 | 10,846,761.591002 | 16,450,256.072173 | 0.422349858243 |
| 0.1 | 10,846,646.950425 | 16,450,240.002277 | 0.422350986830 |
| 1 | 10,845,515.420010 | 16,450,080.388157 | 0.422362196452 |
| 10 | 10,834,600.626697 | 16,448,591.469150 | 0.422466757277 |
| 100 | 10,738,154.216057 | 16,443,305.679671 | 0.422837880682 |
| 1000 | 10,742,161.737361 | 16,823,255.524222 | 0.395857147965 |

Selected **alpha = 100**. Small alpha approaches ordinary least squares; larger alpha shrinks the standardized coefficient vector more strongly. Alpha 1000 did not win validation. We did not revise this choice after inspecting test results.

The final StandardScaler → Ridge pipeline was refitted on all 2,090 rows from 2021/22–2024/25 and evaluated on the same 504 rows from 2025/26 as Linear Regression. The deterministic SVD solver is explicit. Saved-model evaluation reloads this fitted pipeline without fitting or selecting again.

## Scaling and coefficients

StandardScaler subtracts each training feature mean and divides by its training standard deviation (population variance). Minutes are numerically much larger than goals; scaling prevents their arbitrary units from determining the penalty. The scaler is serialized with Ridge. The frozen Linear Regression pipeline remains unscaled.

For z = (x - mean) / scale: beta_original = beta_standardized / scale, and intercept_original = intercept_standardized - sum(beta_original * mean). These equivalent coefficients reproduce pipeline predictions in the original units. Standardized coefficients describe a one-training-standard-deviation change. Original coefficients describe one year, minute, goal or assist. All interpretations hold the other included features constant and are associations, not causal effects.

| Feature | Ridge EUR per standard deviation | Ridge EUR per original unit | Frozen Linear EUR per original unit |
|---|---:|---:|---:|
| age | -5,642,682.517830 | -1,318,456.779072 | -1,390,315.216229 |
| minutes | 5,408,312.812041 | 5,330.453802 | 5,555.885345 |
| goals | 6,736,079.432260 | 1,870,838.084714 | 1,945,189.557058 |
| assists | 4,127,726.027896 | 1,753,487.296459 | 1,724,750.324944 |

Standardized intercept: EUR 20,167,679.425837; original-unit intercept: EUR 40,636,427.585259. The latter is the equation's prediction when all four inputs are zero, not a realistic football scenario.

Age retains a negative association; minutes, goals and assists retain positive associations. Age and goal effects shrink modestly; the assists coefficient increases slightly because correlated inputs can redistribute weight. Ridge shrinks the overall coefficient vector, not necessarily every individual coefficient monotonically.

## Held-out comparison

| Model | MAE (EUR) | RMSE (EUR) | R² |
|---|---:|---:|---:|
| Linear Regression | 11,090,195.645218 | 16,832,743.420461 | 0.452857243619 |
| Ridge Regression | 11,105,366.505469 | 16,933,828.732498 | 0.446266022553 |

Ridge MAE is EUR 11.105367M and RMSE is EUR 16.933829M. MAE worsened by EUR 15,170.860252; RMSE worsened by EUR 101,085.312037; R² changed by -0.006591221066. Ridge did not improve the primary held-out metrics. The training-median comparison MAE remains EUR 16,073,412.698413.

MAE averages absolute prediction errors; RMSE penalizes large errors more heavily; R² compares squared errors against predicting the test-target mean. These are point estimates on one held-out season, not statistical significance claims.

## Prediction analysis

Residual = actual - predicted: positive is model underprediction, negative is model overprediction. Neither establishes that a player is objectively undervalued or overvalued. Predictions are not clipped.

Negative predictions fell from 20 to 16; the minimum increased from EUR -9,232,841.58 to EUR -8,039,864.16. The largest absolute error increased from EUR 109,902,191.31 to EUR 112,011,652.43. The largest overprediction increased from EUR 34,769,851.09 to EUR 34,778,875.69. Thus Ridge does not reduce either the worst underprediction or the worst overprediction, despite fewer negative predictions. Superstar underprediction remains substantial.

### Five closest predictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Nicolás Domínguez | 15,000,000.00 | 14,936,364.06 | 63,635.94 |
| Harrison Reed | 2,000,000.00 | 2,109,515.91 | -109,515.91 |
| Patrick Dorgu | 35,000,000.00 | 35,148,642.49 | -148,642.49 |
| Callum Hudson-Odoi | 30,000,000.00 | 30,152,150.17 | -152,150.17 |
| Angel Gomes | 10,000,000.00 | 10,153,669.13 | -153,669.13 |

### Five largest underpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Erling Haaland | 200,000,000.00 | 87,988,347.57 | 112,011,652.43 |
| Declan Rice | 120,000,000.00 | 41,314,934.30 | 78,685,065.70 |
| William Saliba | 100,000,000.00 | 23,484,982.88 | 76,515,017.12 |
| Moisés Caicedo | 100,000,000.00 | 31,295,397.99 | 68,704,602.01 |
| Alexander Isak | 85,000,000.00 | 17,464,531.45 | 67,535,468.55 |

### Five largest overpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Bruno Fernandes | 35,000,000.00 | 69,778,875.69 | -34,778,875.69 |
| Danny Welbeck | 3,000,000.00 | 32,643,631.03 | -29,643,631.03 |
| Jarrod Bowen | 30,000,000.00 | 56,698,601.02 | -26,698,601.02 |
| Ollie Watkins | 25,000,000.00 | 51,489,710.61 | -26,489,710.61 |
| Raúl Jiménez | 3,000,000.00 | 28,310,112.88 | -25,310,112.88 |

The largest underpredictions remain Haaland, Rice, Saliba, Caicedo and Isak. The largest overpredictions remain Bruno Fernandes, Welbeck, Watkins, Bowen and Jiménez. Regularization does not address omitted position, club strength, nonlinear age effects, or skewed superstar values.

## Running and provenance

```powershell
.venv\Scripts\python.exe -m ml.ridge train
.venv\Scripts\python.exe -m ml.ridge evaluate
```

Existing Ridge artifacts are protected against accidental overwrite. To repeat training, use `--output-dir <fresh-directory>`; `--baseline-dir` defaults to ml/models and supplies the frozen comparison. The separate Ridge CLI keeps the original train/evaluate implementation and its recorded source hashes unchanged. Shared baseline helpers supply validation, splitting, metrics and prediction tables.

Artifacts: ridge.joblib, ridge_metadata.json, ridge_coefficients.json, ridge_test_predictions.csv, ridge_analysis.json, and the updated model_metrics.json. Metadata records candidate scores, split counts, scaler parameters, coefficients, source provenance, dataset and artifact hashes, code hashes, timestamp and library versions. The existing Linear Regression metrics entry is preserved exactly; all five Linear Regression artifacts remain byte-identical.

Dataset SHA256: `1330a7a7190782cb4b231e7cc796626f4106be30dbaf7269dbbf211848e7c514`. Repeat training reproduced selection, parameters, metrics and prediction CSV bytes. Unit tests use synthetic fixtures. The full tests, Ruff lint and formatting check are part of validation.

Limitations inherited from the source remain: incomplete coverage of the full 2025/26 post-season valuation window, selection bias from excluded targets, provider estimates rather than transaction prices, and players recurring across seasons. Alpha selection uses one validation season and six candidates. No confidence intervals or universal superiority claims are implied. Random Forest, XGBoost and Session 5 have not begun.
