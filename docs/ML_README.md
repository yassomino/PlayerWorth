# Machine Learning

Session 9 freezes `playerworth_v1` version 1.0.0 as the V1 production candidate,
trained on all 2,594 rows across five seasons. See [MODEL_CARD_V1.md](MODEL_CARD_V1.md)
and [ML_INPUT_V1.md](ML_INPUT_V1.md). Its evaluation evidence is the existing temporal
OOF backtest; the all-data fit has no unseen test season and no reported test scores.

Session 8 evaluated existing goals/assists per-90 rates in addition to totals and
position. MAE worsened in all four temporal folds, so the rates are not accepted;
the position-only baseline remains preferred. See [PER90_FEATURES.md](PER90_FEATURES.md)
for the full comparison, missing-value policy and descriptive analysis.

Evaluation protocol: 2025/26 has been repeatedly inspected and is an exploratory
held-out season, not an untouched final test. All future feature experiments must
use [TEMPORAL_BACKTESTING.md](TEMPORAL_BACKTESTING.md) before acceptance into the
preferred model. Session 7.5 compares the frozen four-feature and position-aware
XGBoost definitions across four expanding-window folds. Position improves MAE,
RMSE and R² in all four; the retrospective configuration-selection caveat is documented.

Session 3's four-feature Linear Regression baseline is implemented and evaluated on 2025/26.
See [LINEAR_REGRESSION.md](LINEAR_REGRESSION.md) for the actual results, coefficients,
commands, limitations, and learning walkthrough. Later models, target transforms, and
production-model selection described below remain future milestones.

Session 4 Ridge Regression is now evaluated against the frozen corrected baseline.
See [RIDGE_REGRESSION.md](RIDGE_REGRESSION.md) for temporal alpha selection,
scaling, actual results, and commands. Alpha 100 reduced negative predictions but
slightly worsened held-out MAE, RMSE and R².

Session 5 Random Forest is evaluated on the same four features and frozen dataset.
See [RANDOM_FOREST.md](RANDOM_FOREST.md) for all 24 temporal-validation candidates,
selected parameters, prediction analysis and commands. Held-out MAE improved by
8.61% against Linear Regression.

Session 6 XGBoost is evaluated with the same four inputs and frozen dataset.
See [XGBOOST.md](XGBOOST.md) for temporal early stopping, the 18-candidate search,
and actual results. XGBoost improves held-out MAE by 0.443% against Random Forest.
That experiment was not itself designated for deployment; Session 9 creates a separate all-data artifact.

Session 7 adds only one-hot encoded position under the frozen XGBoost settings.
See [POSITION_FEATURE.md](POSITION_FEATURE.md) for cohort counts, position-level
errors and historical-metadata limitations. Held-out MAE improves by 0.959%.
Position is unverified historical snapshot metadata; further features remain future work.

## Goal

Train, evaluate, compare, and save PlayerWorth market-value regression models.

Start with Linear Regression. Keep it in the final product even if another model performs better.

## Problem

Supervised regression:

```text
X = player statistics + context
y = market_value_eur
```

## Milestone 1 — Linear Regression

Start with a small feature set:

```text
age
minutes
goals
assists
```

Train:

```python
LinearRegression()
```

Evaluate:

- MAE
- RMSE
- R²

Do not judge quality using training-set performance.

## Splitting

Support both:

### Simple prototype split
Random train/test split with fixed random seed.

### Better evaluation
Season-based split, for example:

```text
Train: 2021/22, 2022/23, 2023/24
Test: 2024/25
```

Keep this configurable.

## Preprocessing

Use `Pipeline` + `ColumnTransformer`.

Numerical:
- imputation
- optional scaling

Categorical:
- imputation
- `OneHotEncoder(handle_unknown="ignore")`

Save preprocessing and model together.

## Feature Engineering

Reusable functions for:

```text
goals_per_90
assists_per_90
goal_contributions_per_90
shots_per_90
key_passes_per_90
tackles_per_90
interceptions_per_90
```

Formula:

```text
stat_per_90 = stat / minutes * 90
```

Handle zero minutes safely.

## Target Transformation Experiment

Test:

```python
np.log1p(market_value_eur)
```

Invert predictions using:

```python
np.expm1(prediction)
```

Compare against the raw-target baseline.

## Required Models

1. Linear Regression
2. Ridge Regression
3. Random Forest Regressor
4. XGBoost Regressor

Do them sequentially, not all at once.

## Metrics Output

Generate:

```text
ml/models/model_metrics.json
```

Example schema:

```json
[
  {
    "model": "linear_regression",
    "mae": 0,
    "rmse": 0,
    "r2": 0
  }
]
```

Values must come from actual evaluation.

## Interpretability

Linear models:
- coefficients
- transformed feature names

Tree models:
- feature importance where appropriate

SHAP is optional later.

## Model Files

```text
ml/models/
├── linear_regression.joblib
├── ridge.joblib
├── random_forest.joblib
├── xgboost.joblib
├── production_model.joblib
├── model_metrics.json
└── metadata.json
```

## Metadata

Store:

- model name
- model version
- feature list
- dataset version/hash
- hyperparameters
- split strategy
- metrics
- training timestamp
- Git commit if available

## Important Rule

Do **not** return arbitrary "confidence = 92%" values. If uncertainty is added later, implement a defensible method such as prediction intervals or calibrated uncertainty.

## Acceptance Criteria

- Linear Regression baseline trained
- preprocessing saved with model
- MAE/RMSE/R² measured
- Ridge evaluated
- Random Forest evaluated
- XGBoost evaluated
- comparison file generated
- production model selected
- inference uses identical preprocessing
- training is reproducible

## First Codex Prompt

```text
Read README.md, docs/DATA_README.md, and docs/ML_README.md.

Implement only ML milestone 1:
1. reusable feature-engineering functions
2. preprocessing pipeline
3. configurable split
4. Linear Regression baseline
5. MAE, RMSE, and R² evaluation
6. joblib serialization
7. tests

Do not add Random Forest or XGBoost yet.
Do not fabricate metrics.
```
