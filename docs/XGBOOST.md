# Session 6 - PlayerWorth XGBoost

XGBoost 3.4.1 uses the unchanged 2,594 observations, age/minutes/goals/assists inputs and untransformed market_value_eur target. No rows were removed. The previous three models and dataset remain frozen. This is an experiment, not a designated production model.

## Boosting in PlayerWorth

Random Forest builds independent bootstrap trees and averages their predictions. XGBoost adds trees sequentially to correct the current ensemble. With squared-error regression, remaining errors guide subsequent trees. If early predictions miss combinations of young age, high minutes and strong production, later trees may reduce those residuals. That is an illustration, not a claim about a particular learned split or a guarantee of better held-out performance.

No scaling is applied: threshold splits operate on ordered values. No feature engineering, target transform or clipping was added. Shared validation rejects missing/invalid inputs. The final sklearn Pipeline contains XGBRegressor with objective reg:squarederror, CPU hist trees, random_state=42, n_jobs=1 and gain importance.

## The search and early stopping

The predeclared reduced search has 18 candidates: depths 2/4/6 times learning rates 0.03/0.05/0.1 times two profiles. Profile A uses min_child_weight=1, subsample=1.0, colsample_bytree=1.0. Profile B uses min_child_weight=5, subsample=0.8, colsample_bytree=0.8. Coupling these regularization settings keeps the experiment small; it does not explore every combination in the suggested full grid.

Every candidate fits 1,547 rows from 2021/22-2023/24 and uses only the 543 rows from 2024/25 as eval_set. Maximum rounds=800; early stopping patience=50; monitored metric=MAE. Selection ranks independently calculated validation MAE, then RMSE with EUR 0.01 equivalence tolerance, then higher R2 with 1e-12 tolerance, then smaller depth, fewer effective rounds and larger child weight. The selection function rejects the test season.

| Depth | Rate | Profile | Effective rounds | Validation MAE EUR | RMSE EUR | R2 |
|---:|---:|---|---:|---:|---:|---:|
| 2 | 0.03 | A | 582 | 9,707,839.409523 | 15,722,049.405593 | 0.472359805085 |
| 2 | 0.03 | B | 476 | 9,660,242.989044 | 15,294,972.256916 | 0.500636326842 |
| 2 | 0.05 | A | 392 | 9,755,286.514316 | 15,878,149.587085 | 0.461830183004 |
| 2 | 0.05 | B | 337 | 9,670,270.008100 | 15,299,376.541912 | 0.500348695514 |
| 2 | 0.1 | A | 217 | 9,705,198.257992 | 15,796,338.233028 | 0.467361680759 |
| 2 | 0.1 | B | 160 | 9,638,620.294976 | 15,406,458.857723 | 0.493329970442 |
| 4 | 0.03 | A | 157 | 9,812,521.380525 | 15,793,734.160808 | 0.467537280230 |
| 4 | 0.03 | B | 196 | 9,665,572.297940 | 15,441,536.058308 | 0.491020186139 |
| 4 | 0.05 | A | 79 | 9,861,208.681400 | 15,867,207.096681 | 0.462571691180 |
| 4 | 0.05 | B | 80 | 9,683,332.052256 | 15,514,334.668446 | 0.486209736515 |
| 4 | 0.1 | A | 47 | 9,839,145.274401 | 15,822,217.069888 | 0.465615028966 |
| 4 | 0.1 | B | 63 | 9,562,915.187615 | 15,445,367.562564 | 0.490767568749 |
| 6 | 0.03 | A | 94 | 9,908,017.456722 | 15,957,897.721421 | 0.456410682863 |
| 6 | 0.03 | B | 102 | 9,762,530.302486 | 15,710,544.235183 | 0.473131761592 |
| 6 | 0.05 | A | 47 | 9,872,482.046501 | 16,029,519.299525 | 0.451520302747 |
| 6 | 0.05 | B | 63 | 9,758,793.911142 | 15,626,894.697627 | 0.478727360848 |
| 6 | 0.1 | A | 34 | 9,874,569.108195 | 15,830,508.849309 | 0.465054783415 |
| 6 | 0.1 | B | 31 | 9,809,228.373158 | 15,791,448.639612 | 0.467691375110 |

**Winner: depth 4, learning_rate=0.1, min_child_weight=5, subsample=0.8, colsample_bytree=0.8.** Best iteration is 62 (zero-based), so the final fit uses 63 rounds. Validation MAE is EUR 9,562,915.187615, RMSE EUR 15,445,367.562564, R2 0.490767568749. XGBoost reports its internal best MAE as EUR 9,562,915.169717; the approximately EUR 0.018 difference is numerical metric precision, not a different dataset. All comparisons use the shared sklearn metrics.

The candidate may contain later patience-round trees, but sklearn predict uses best_iteration automatically. Final refitting creates a fresh estimator on all 2,090 training rows from 2021/22-2024/25, with exactly 63 rounds and no early stopping or eval_set. Only then are the 504 rows from 2025/26 evaluated. The test results never revise this choice. See the [official XGBoost sklearn API](https://xgboost.readthedocs.io/en/stable/python/python_api.html) for best_iteration behavior.

## What the chosen settings mean

- Learning rate 0.1 reduces each new tree contribution. Smaller rates usually need more trees; they do not guarantee better predictions.
- 63 rounds balance fitting remaining patterns against fitting noise, using the earlier validation season. Too few rounds can underfit; too many can overfit.
- Depth 4 limits each tree to four split levels, constraining interactions and complexity.
- min_child_weight=5 requires enough summed second-derivative weight in a child. Under this unweighted squared-error objective, it behaves like a minimum sample-support constraint; it is not literally the Random Forest leaf-size parameter for all objectives.
- subsample=0.8 samples 80% of rows per boosting iteration, adding regularization.
- colsample_bytree=0.8 uses a subset of the four features per tree, adding feature randomness.
- Early stopping asks whether the later 2024/25 season still improves, without consulting 2025/26.

## Held-out comparison

| Model | MAE EUR | RMSE EUR | R2 |
|---|---:|---:|---:|
| linear_regression | 11,090,195.645218 | 16,832,743.420461 | 0.452857243619 |
| ridge | 11,105,366.505469 | 16,933,828.732498 | 0.446266022553 |
| random_forest | 10,135,335.817899 | 16,081,107.851481 | 0.500629623030 |
| xgboost | 10,090,465.831721 | 15,947,555.471390 | 0.508889646727 |

Against linear_regression: MAE improves EUR 999,729.813496 (9.014537%); RMSE improves EUR 885,187.949071; R2 increases 0.056032403108.

Against ridge: MAE improves EUR 1,014,900.673748 (9.138831%); RMSE improves EUR 986,273.261108; R2 increases 0.062623624174.

Against random_forest: MAE improves EUR 44,869.986178 (0.442708%); RMSE improves EUR 133,552.380091; R2 increases 0.008260023697.

XGBoost improves all three held-out point estimates, but the MAE gain over Random Forest is only 0.443%. This is not a statistical significance claim. Median absolute error actually increases from about EUR 6.035M to EUR 6.090M, so the aggregate improvement does not mean every player or error summary improves.

## Gain importance

| Feature | Normalized average gain |
|---|---:|
| goals | 0.411629945040 |
| assists | 0.234950676560 |
| age | 0.213111445308 |
| minutes | 0.140307903290 |

Gain is average training-objective improvement for splits using the feature. The saved file includes raw average gain and normalized shares. A feature unused in splits is explicitly reported as zero. These numbers describe model usefulness, not causal effects, and should not be compared directly to Random Forest impurity values or linear coefficients. Correlated inputs complicate interpretation.

## Prediction range and errors

| Quantity | EUR |
|---|---:|
| minimum_training_target_eur | 75,000.000000 |
| maximum_training_target_eur | 180,000,000.000000 |
| minimum_prediction_eur | 525,205.562500 |
| maximum_prediction_eur | 125,509,216.000000 |
| median_absolute_error_eur | 6,089,521.000000 |
| worst_absolute_error_eur | 81,898,344.000000 |

Negative predictions: **0**, without clipping. Unlike Random Forest averages, sums of boosted leaf corrections are not mathematically bounded by training-target extrema and can produce negative values. Nevertheless tree predictions remain piecewise constant outside learned split thresholds; boosting does not provide linear extrapolation. Here every test prediction remains within the EUR 75,000-180M training range. It has not solved the EUR 200M superstar problem.

Residual = actual - predicted; positive means underprediction. Rankings are prediction errors, not objective player valuation judgments.

### Five closest predictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Chadi Riad | 15,000,000.00 | 14,955,463.00 | 44,537.00 |
| Harrison Armstrong | 12,000,000.00 | 12,103,987.00 | -103,987.00 |
| Alphonse Areola | 4,000,000.00 | 4,110,568.25 | -110,568.25 |
| Marc Guiu | 12,000,000.00 | 11,875,549.00 | 124,451.00 |
| Max Alleyne | 8,000,000.00 | 7,873,217.00 | 126,783.00 |

### Five largest underpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Erling Haaland | 200,000,000.00 | 118,101,656.00 | 81,898,344.00 |
| Declan Rice | 120,000,000.00 | 46,780,152.00 | 73,219,848.00 |
| William Saliba | 100,000,000.00 | 27,099,846.00 | 72,900,154.00 |
| Moisés Caicedo | 100,000,000.00 | 31,037,976.00 | 68,962,024.00 |
| Cole Palmer | 100,000,000.00 | 34,088,748.00 | 65,911,252.00 |

### Five largest overpredictions

| Player | Actual EUR | Predicted EUR | Residual EUR |
|---|---:|---:|---:|
| Igor Thiago | 65,000,000.00 | 125,509,216.00 | -60,509,216.00 |
| Santiago Bueno | 10,000,000.00 | 34,191,904.00 | -24,191,904.00 |
| Jaidon Anthony | 20,000,000.00 | 44,156,604.00 | -24,156,604.00 |
| Hugo Bueno | 12,000,000.00 | 34,430,900.00 | -22,430,900.00 |
| Ollie Watkins | 25,000,000.00 | 47,180,876.00 | -22,180,876.00 |

### Named-player comparison (analysis only)

| Player | Actual EUR | Random Forest EUR | XGBoost EUR |
|---|---:|---:|---:|
| Declan Rice | 120,000,000.00 | 47,779,696.05 | 46,780,152.00 |
| Erling Haaland | 200,000,000.00 | 101,107,030.21 | 118,101,656.00 |
| William Saliba | 100,000,000.00 | 25,635,060.84 | 27,099,846.00 |
| Cole Palmer | 100,000,000.00 | 31,546,042.28 | 34,088,748.00 |
| Moisés Caicedo | 100,000,000.00 | 32,519,069.26 | 31,037,976.00 |

Haaland, Saliba and Palmer underpredictions improve; Rice and Caicedo worsen. Haaland still has an EUR 81.898M residual. Igor Thiago is overpredicted by EUR 60.509M, compared with EUR 22.758M under Random Forest. These observations did not influence parameter selection.

## Running and verification

```powershell
.venv\Scripts\python.exe -m ml.xgboost_model train
.venv\Scripts\python.exe -m ml.xgboost_model evaluate
```

Existing XGBoost artifacts are protected against overwrite; use --output-dir with a fresh directory to rerun. --baseline-dir defaults to ml/models. The evaluation command reloads without training or retuning. The first real run performs the final held-out evaluation once; reproducibility verification repeats selection and training, compares serialized booster bytes, and checks reloaded predictions against the recorded test CSV rather than conducting another selection/evaluation experiment.

Artifacts: xgboost.joblib, xgboost_metadata.json, xgboost_feature_importance.json, xgboost_test_predictions.csv and xgboost_analysis.json; model_metrics.json preserves the existing entries and adds the measured XGBoost result. Joblib is consistent with this repository; load under the pinned environment rather than treating it as a cross-version interchange format. Metadata records versions, full candidate results, early-stopping scores/round counts, final parameters, provenance, hashes and timestamp.

Repeated selection and native booster bytes matched exactly. Reloaded predictions matched the saved CSV. Dataset and all 15 previous model artifacts retained their hashes. Synthetic tests cover temporal isolation including eval_set, final round counts, serialization, schemas and prior-artifact preservation.

Dataset SHA256: `1330a7a7190782cb4b231e7cc796626f4106be30dbaf7269dbbf211848e7c514`.

## Limitations

Only four inputs are included. Position, club strength and richer match statistics remain absent. Market values incorporate context outside match performance. Extrapolation is limited, and superstar errors remain large. Selection uses one validation season and a reduced grid that couples three regularization settings. The same test season has now been used to compare four model families, so further test-driven iteration risks optimistic conclusions. Repeated players across seasons and incomplete post-season valuation export coverage remain inherited limitations. No feature expansion, application work or next session was begun.
