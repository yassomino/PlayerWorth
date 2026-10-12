# PlayerWorth V1 inference contract

Version 1.0.0. Exactly five fields are required in each mapping or DataFrame row. Extra fields are rejected, including player IDs, targets and rejected rates. Columns are reordered internally to age, minutes, goals, assists, position. Batch order is preserved; empty batches are rejected.

| Field | Accepted values |
|---|---|
| age | Real numeric, finite, nonnegative; fractional values allowed |
| minutes | Real numeric, finite, nonnegative; fractional values allowed |
| goals | Real numeric, finite, nonnegative and integer-compatible (2 or 2.0) |
| assists | Same rules as goals |
| position | String, including pandas categorical string values, or missing value (None, NaN, pandas NA) |

Numeric strings and booleans are rejected. No arbitrary upper football limits are imposed. Acceptance is not a claim that extreme hypothetical inputs are plausible or within the training distribution. Missing numeric inputs are rejected. The position field must exist, but its value may be missing.

The serialized pipeline strips position whitespace and uppercases it. AM, CB, CM, DM, FB, GK, ST, W and UNKNOWN are supported. Missing, blank or unmapped strings become UNKNOWN. OneHotEncoder(handle_unknown="ignore", sparse_output=False) provides categorical indicators. Numerical fields pass through without scaling. No caller should implement its own encoder.

## Python usage

```python
from ml.inference import load_model, predict_batch, predict_player_value

model = load_model()  # resolves ml/models/current_model.json
value = predict_player_value(
    age=24, minutes=3000, goals=15, assists=8, position="ST", model=model
)
values = predict_batch([
    {"age": 24, "minutes": 3000, "goals": 15, "assists": 8, "position": "ST"},
    {"age": 27, "minutes": 2800, "goals": 1, "assists": 1, "position": "CB"},
], model=model)
```

load_model(path) also accepts an explicit artifact path with its sibling playerworth_v1_metadata.json. Loading checks the recorded artifact hash and feature contract. Only load trusted project joblib artifacts; serialization is not a sandbox. Keep the project modules and pinned dependency environment available. Load once and reuse the model for batches; inference never trains.

Single prediction returns a Python float; batch prediction returns a one-dimensional float NumPy array in input order. Values are EUR, finite, unrounded, unclipped, without currency text or confidence scores. Negative outputs remain negative. UI formatting or future application policy belongs outside this ML layer.

## CLI smoke check

```powershell
.venv\Scripts\python.exe -m ml.inference --age 24 --minutes 3000 --goals 15 --assists 8 --position ST
```

The frozen V1 artifact returned `{"predicted_market_value_eur": 82459040.0}`. This is a hypothetical inference-path check, not a measured transfer valuation or evaluation metric.
