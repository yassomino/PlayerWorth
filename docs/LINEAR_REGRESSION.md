# Session 3 — PlayerWorth Linear Regression baseline

This is the first interpretable baseline, not a production or final model. It uses the real 2,594-row Premier League dataset from Session 2.5. No additional model, feature engineering, target transform, tuning, API, database, or frontend was added.

## What enters this model: X and y

For PlayerWorth, `X` is a table with exactly four columns in this order: `age`, `minutes`, `goals`, `assists`. Age is historical age at season end; the other three values summarize matches from that exact EPL season. These are a small, understandable set of available attributes that might be associated with market value. They are not claimed to be a complete explanation of value.

`y` is the corresponding `market_value_eur` column: the historical Transfermarkt valuation selected on or after season end, within 45 days. Each row has one number to estimate. This makes the task supervised regression: training examples supply both the inputs and a continuous target. Transfermarkt estimates are observed labels here, not actual transfer prices or objective true values.

`select_features()` in `ml/baseline.py` explicitly selects and orders the four columns. Names, IDs, clubs, position, dates, valuations, and per-90 fields never enter `fit()` or `predict()`. Names and IDs are retained only to identify rows in the prediction analysis.

## The data actually inspected

| Item | Observed value |
| --- | --- |
| Shape | 2,594 rows × 24 columns |
| Input and target dtypes | All int64 |
| Missing age/minutes/goals/assists/target | Zero in every selected column |
| Negative or nonfinite selected values | None |
| Duplicate player-season rows | None |
| Target minimum | €75,000 |
| Target median | €15,000,000 |
| Target mean | €21,096,164.23 |
| Target 75th percentile | €28,000,000 |
| Target 95th percentile | €65,000,000 |
| Target maximum | €200,000,000 |

Age ranges from 16–40, minutes from 1–3,420, goals from 0–36, and assists from 0–21. No rows were removed during this ML session. The target is strongly right-skewed: a small number of very expensive players sit far above the typical value.

## The temporal test

| Season | Role | Rows |
| --- | --- | ---: |
| 2021/22 | Train | 491 |
| 2022/23 | Train | 522 |
| 2023/24 | Train | 534 |
| 2024/25 | Train | 543 |
| 2025/26 | Test | 504 |

We fit on **2,090 past-season rows** and evaluate on **504 later-season rows**. The test season is never shuffled into training. All five expected seasons must be present; unexpected or missing seasons cause an error rather than silent filtering.

This measures generalization to an unseen **season**, not exclusively to unseen people: 375 of the 504 test players have an earlier training-season observation. Their future observations and targets are still excluded from fitting. No tuning or model selection was performed on this holdout.

## What fit and predict do

```python
pipeline = Pipeline([("linear_regression", LinearRegression())])
pipeline.fit(X_train, y_train)
predicted = pipeline.predict(X_test)
```

`fit()` uses scikit-learn ordinary least squares to choose four coefficients and one intercept that minimize the sum of squared training residuals. It does not memorize the test labels or manually encode football rules. PlayerWorth calls scikit-learn rather than implementing this optimization itself. See the [LinearRegression documentation](https://scikit-learn.org/1.7/modules/generated/sklearn.linear_model.LinearRegression.html).

`predict()` applies those already learned coefficients to each test row. It does not refit the model. A saved joblib Pipeline carries the fitted estimator into later evaluation so the same model is used.

Because every selected feature is complete, the pipeline has no imputer, scaler, or ColumnTransformer. Their additional machinery is unnecessary for this four-column baseline. Validation explicitly fails on missing/invalid values, instead of discarding rows or silently filling them. Inputs stay in years, minutes, goals, and assists, so coefficients remain directly interpretable in these units.

## The fitted equation and coefficients

Predicted EUR = intercept + age coefficient × age + minutes coefficient × minutes + goals coefficient × goals + assists coefficient × assists.

| Term | Fitted value | Conditional interpretation |
| --- | ---: | --- |
| Age | €-1,390,315.216229 per year | One additional year is associated with this decrease, holding minutes, goals, and assists fixed. |
| Minutes | €5,555.885345 per minute | One additional minute is associated with this increase, holding age, goals, and assists fixed. |
| Goals | €1,945,189.557058 per goal | One additional goal is associated with this increase, holding age, minutes, and assists fixed. |
| Assists | €1,724,750.324944 per assist | One additional assist is associated with this increase, holding age, minutes, and goals fixed. |
| Intercept | €42,097,703.716638 | Mathematical starting value when all four inputs equal zero. |

These coefficients describe conditional associations learned from this training sample; they do not prove causation. For example, scoring one extra goal does not guarantee a real transfer valuation increase of that amount. Correlated playing time, scoring, omitted position, and other omitted attributes all affect the fitted coefficients.

The intercept lets the fitted plane shift up or down. An age-zero player with zero minutes, goals, and assists is outside our data and has no useful standalone football interpretation. The intercept is a mathematical parameter, not a youth-player valuation. Coefficients and intercept are stored at full floating-point precision in `linear_regression_coefficients.json`; table values are display-rounded only.

## Actual held-out metrics

| Method | MAE (EUR) | MAE (€M) | RMSE (EUR) | RMSE (€M) | R² |
| --- | ---: | ---: | ---: | ---: | ---: |
| Linear Regression | 11,090,195.645218 | 11.090196 | 16,832,743.420461 | 16.832743 | 0.452857109015 |
| Training-median guess | 16,073,412.698413 | 16.073413 | 24,835,209.061471 | 24.835209 | -0.191040315513 |

**MAE** averages the absolute error across the 504 test rows. Here the mean error magnitude is **€11,090,195.65 (€11.090196M)**. This is an average across players, not a prediction interval, confidence level, or guarantee for an individual player.

**RMSE** squares each error, averages those squares, and takes the square root. Its value is **€16,832,743.42 (€16.832743M)**. It is larger than MAE because large mistakes receive extra weight before averaging. The high-value underpredictions below help explain the gap.

**R²** is **0.452857109015**: the model's squared error is about 45.29% lower than a constant prediction equal to the test target mean. This is not 45.29% accuracy or confidence. R² can be negative; the training-median guess has a negative score here. The [scikit-learn R² definition](https://scikit-learn.org/1.7/modules/generated/sklearn.metrics.r2_score.html) specifies this comparison. For constant targets or fewer than two rows, our metric helper returns an explicit JSON null instead of a misleading R².

The sanity baseline predicts the **training median of €15,000,000** for every test player. It uses no test values to choose that constant and is not another fitted ML model. Linear Regression's MAE is **31.002856% lower**. The median comparator lives in metadata, while `model_metrics.json` contains only the trained Linear Regression entry.

## A real residual

We use **residual = actual − predicted**. Positive means the model underpredicted; negative means it overpredicted. Absolute error is the magnitude of that residual.

For **Chris Rigg** in 2025/26, the inputs are age **18**, minutes **766**, goals **1**, assists **1**. The observed target is **€25,000,000.00** and the model predicts **€24,997,777.88**. The residual is **+€2,222.12**, so the model underpredicted by that amount.

## Five closest predictions and largest errors

All rows below are actual held-out predictions. These describe model errors, not objective overvaluation or undervaluation. Values are rounded to cents for display; the CSV retains floating-point predictions.

### Five smallest absolute errors

| Player | Actual EUR | Predicted EUR | Residual EUR |
| --- | ---: | ---: | ---: |
| Chris Rigg | 25,000,000.00 | 24,997,777.88 | +2,222.12 |
| Freddie Woodman | 3,000,000.00 | 2,956,410.14 | +43,589.86 |
| Nathan Patterson | 10,000,000.00 | 10,063,551.01 | -63,551.01 |
| Angel Gomes | 10,000,000.00 | 9,923,310.00 | +76,690.00 |
| Pablo | 18,000,000.00 | 17,835,792.35 | +164,207.65 |


### Five largest model underpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
| --- | ---: | ---: | ---: |
| Erling Haaland | 200,000,000.00 | 90,097,808.69 | +109,902,191.31 |
| Declan Rice | 120,000,000.00 | 41,630,892.06 | +78,369,107.94 |
| William Saliba | 100,000,000.00 | 23,813,653.04 | +76,186,346.96 |
| Moisés Caicedo | 100,000,000.00 | 31,858,048.26 | +68,141,951.74 |
| Alexander Isak | 85,000,000.00 | 17,410,058.60 | +67,589,941.40 |


### Five largest model overpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
| --- | ---: | ---: | ---: |
| Bruno Fernandes | 35,000,000.00 | 69,769,851.09 | -34,769,851.09 |
| Danny Welbeck | 3,000,000.00 | 33,038,521.91 | -30,038,521.91 |
| Ollie Watkins | 25,000,000.00 | 52,542,027.89 | -27,542,027.89 |
| Jarrod Bowen | 30,000,000.00 | 57,197,535.17 | -27,197,535.17 |
| Raúl Jiménez | 3,000,000.00 | 28,335,020.01 | -25,335,020.01 |


## What this first model misses

Market value is not perfectly linear. The same additional goal or minute need not carry the same association for every player. Age effects may rise and then fall over a career; this model applies a single negative age slope everywhere.

Position is deliberately ignored, so a goalkeeper or defender is judged by the same four-variable equation as a striker. Club strength, contract situation, reputation, and other context are absent. Richer passing, defensive, and shot metrics are unavailable in the current source. Superstar values occupy a long upper tail and can be very difficult to estimate from these four inputs; Erling Haaland is the largest underprediction in this holdout.

The unrestricted linear equation also produces **20 negative test predictions**, with a minimum of **€-9,232,841.58**. These are not plausible market values. They are retained, not clipped, so the baseline's shortcomings and metrics remain transparent. No correction, log target transform, or alternative model was added in this session.

The corrected dataset requires season_end_date <= market_value_date <= season_end_date + 45 days. Full-season features now always precede or coincide with the target date at daily resolution. All 24 pre-end-only rows were removed (18 training, six test); none had a replacement target inside the new window. No appearance statistics were truncated and no following-season data was added. The remaining limits include 137 candidates without valid targets, possible selection bias, and the truncated 2025/26 valuation export.

## Run, reload, and reproduce

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m ml.train --model linear
.\.venv\Scripts\python.exe -m ml.evaluate
```

Existing training artifacts are protected. For a second run use `--output-dir <new-directory>`; evaluate it with `--model-path <new-directory>/linear_regression.joblib`. `--dataset` can select another file, but the fixed Session 3 seasons and validation contract still apply. Evaluation verifies dataset/model hashes against metadata, reloads the saved Pipeline, and never calls `fit()`. Load only trusted local joblib artifacts.

The same dataset and configuration produce equivalent coefficients, intercept, and evaluation results. No random split or stochastic estimator is used. Floating-point details can differ across numerical-library/platform versions, so versions are pinned/recorded. The training timestamp is expected to differ between runs and is not part of parameter equivalence.

Dataset SHA-256: `1330a7a7190782cb4b231e7cc796626f4106be30dbaf7269dbbf211848e7c514`. scikit-learn version: `1.7.2`. Metadata also records source provenance, cleaning-report hash, training code hashes, model hash, prediction-file hash, complete inspection results, and the temporal split.

## Files and tests

- `ml/baseline.py`: feature validation/selection, fixed temporal split, Pipeline construction, shared metrics, coefficients, prediction schema, and error analysis.
- `ml/train.py`: fitting and artifact generation.
- `ml/evaluate.py`: saved-model evaluation without retraining.
- `ml/tests/test_linear_regression.py`: small synthetic tests for features, temporal isolation, metrics, fitting, coefficients, serialization, metadata, prediction schema, reproducibility, and changing test targets without changing fitted parameters.
- `ml/models/linear_regression.joblib`: fitted Pipeline.
- `ml/models/linear_regression_metadata.json`: training/evaluation provenance and median comparison.
- `ml/models/linear_regression_coefficients.json`: full-precision coefficients and intercept.
- `ml/models/linear_regression_test_predictions.csv`: all 504 test predictions and residuals.
- `ml/models/linear_regression_analysis.json`: the three real top-five error analyses.
- `ml/models/model_metrics.json`: an extensible list containing only Linear Regression.
- `pyproject.toml` and `requirements-dev.txt`: pinned scikit-learn/joblib/SciPy dependencies alongside the existing numerical stack.

Generated model artifacts remain ignored by Git under the existing rules. The human-readable learning report is tracked source documentation. No production-model alias was created, and Session 4 has not begun.

## Temporal leakage correction compared with the previous run

The model implementation, feature list, and season split are unchanged. Only target eligibility changed from −30/+45 days to 0/+45 days. Previous artifacts and dataset are preserved under `ml/models/archive/pre_postseason_correction/`; `ml/models/temporal_policy_comparison.json` records the differences and removed identities.

| Measure | Previous | Corrected | Change |
| --- | ---: | ---: | ---: |
| MAE | 11,049,513.290587582 | 11,090,195.645217676 | +40,682.354630094 |
| RMSE | 16,767,759.717619648 | 16,832,743.420460839 | +64,983.702841191 |
| R2 | 0.455378109 | 0.452857244 | -0.002520865 |

These metric changes include a changed evaluation cohort (510 to 504 rows), so they are not a like-for-like model improvement comparison. There are zero pre-end targets in both training and test data. Session 4 remains unstarted.
