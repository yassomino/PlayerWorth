# PlayerWorth API — Session 11

The local FastAPI application connects the existing PostgreSQL layer to the frozen
PlayerWorth V1 model. No model training, migrations, hosted deployment, authentication
or frontend features are introduced here.

## Start locally

From the repository root, activate the virtual environment or use its Python explicitly:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# Start PostgreSQL as described in DATABASE.md, then set DATABASE_URL.
# On the Session 10 workstation, load the existing ignored local credentials:
. ./.local/database-env.ps1
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m scripts.seed_database
.venv\Scripts\python.exe -m backend.app.main
```

Open http://127.0.0.1:8000/docs for interactive documentation and
http://127.0.0.1:8000/openapi.json for the generated schema.
Product base URL: **http://127.0.0.1:8000/api/v1**.

For code reload during development:

```powershell
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The module entry point honors API_HOST/API_PORT; Uvicorn's direct CLI uses its own
host/port flags. Python reads process environment variables, not `.env` automatically.
Compose still reads `.env` for PostgreSQL. Never commit real credentials.

| Environment variable | Behavior |
|---|---|
| DATABASE_URL | Required PostgreSQL connection URL; existing Session 10 engine factory |
| MODEL_POINTER_PATH | Defaults to repository-relative `ml/models/current_model.json` |
| CORS_ORIGINS | Comma-separated explicit origins; default `http://localhost:3000`; empty disables CORS |
| API_HOST | Default `127.0.0.1`, module launcher only |
| API_PORT | Default `8000`, module launcher only |
| TEST_DATABASE_URL | Dedicated PostgreSQL integration-test database only |

## Architecture and lifecycle

`main.py` owns lifespan, CORS, safe error handlers and application creation.
`routes.py` handles HTTP; `schemas.py` defines request/response contracts; services
perform database queries and orchestrate inference. `dependencies.py` supplies a
session per request from the application-level Session 10 factory. Closing the
session rolls back uncommitted work; explicit writes commit before returning success.
Startup checks the database and registered candidate. No tables are created by the API.

Each process loads the configured pointer and metadata once, verifies name/version,
and calls the existing `ml.inference.load_model` for artifact hash and feature-contract
verification. The pointer must identify sibling V1 files, including the existing
loader's `playerworth_v1_metadata.json` filename. Database registration must match
the candidate name/version, dataset hash, feature list and hyperparameters and have
`is_production=True`. Missing/corrupt/unregistered candidates fail startup clearly;
there is no silent fallback. Restart the process to change the configured candidate.

Inference always goes through `ml.inference.predict_batch`, including single-row
requests. Position preprocessing and feature ordering remain inside the existing
pipeline. Synchronous route handlers run through FastAPI's thread pool; rankings
predict one season as a batch. No model is loaded per request/player.
This follows FastAPI's [lifespan guidance](https://fastapi.tiangolo.com/advanced/events/).

## Endpoints

All paths below have prefix `/api/v1`. Public player IDs are internal database IDs.

| Method | Path | Behavior |
|---|---|---|
| GET | `/health` | Lightweight database query and loaded-model identity |
| GET | `/players` | Partial normalized-name search; `search`, `limit=20` (max 100), `offset=0` |
| GET | `/players/{player_id}` | Profile, seasons and historical values; newest first |
| GET | `/players/{player_id}/prediction` | Selected/latest season estimate; optional `season=2024/25` |
| POST | `/predictions` | Exactly five V1 fields; optional `persist=false` query flag |
| POST | `/players/{player_id}/simulate` | Partial overrides; optional `season`, `persist=false` |
| GET | `/models/current` | Preferred candidate, public-safe metadata and temporal OOF metrics |
| GET | `/models` | Registered versions only; `limit=20` (max 100), `offset=0` |
| GET | `/rankings/undervalued` | Positive model differences, largest first; optional `season`, `limit=20` (max 50) |
| GET | `/rankings/overvalued` | Negative model differences, most negative first; same query parameters |

Search results are ordered by normalized name then internal ID. `%` and `_` are
literal search characters, not SQL wildcard controls. Latest known club means
the primary club in the latest stored season, not verified current club membership.
Detail seasons sort by season descending; values sort by date then ID descending.
Relationships are fetched in batches rather than one query per season/player.

## Prediction contract and examples

Exactly `age`, `minutes`, `goals`, `assists`, `position` are accepted. Numeric inputs
must be JSON numbers, finite and nonnegative; booleans and numeric strings are
rejected. Goals and assists must be integer-compatible. Position is a required key
but may be null; unknown strings use the frozen model's handling. Extra fields,
including IDs, targets and per-90 features, are rejected. No narrow football bounds
are invented. See [ML_INPUT_V1.md](ML_INPUT_V1.md).

```powershell
$base = 'http://127.0.0.1:8000/api/v1'
Invoke-RestMethod "$base/players?search=haaland&limit=10"
Invoke-RestMethod "$base/players/582"
Invoke-RestMethod "$base/players/582/prediction?season=2025/26"
Invoke-RestMethod "$base/predictions" -Method Post -ContentType 'application/json' `
  -Body '{"age":24,"minutes":3000,"goals":15,"assists":8,"position":"ST"}'
```

Actual V1 response to that five-feature example:

```json
{
  "model_name": "playerworth_v1",
  "model_version": "1.0.0",
  "input": {"age":24.0,"minutes":3000.0,"goals":15.0,"assists":8.0,"position":"ST"},
  "predicted_value_eur": 82459040.0,
  "prediction_id": null
}
```

In the validated local database, search returns Erling Haaland with internal ID 582
(provider ID 418560), latest season 2025/26, Manchester City. IDs are not guaranteed
to match a separately populated database: obtain them from search. His profile has
four retained seasons and four valuations. Latest source statistics: age 25,
2,959 minutes, 27 goals and eight assists. His season estimate is 148951056 EUR,
observed value 200000000 EUR and `difference_eur=-51048944`.

Observed values for predictions/rankings use the earliest `transfermarkt` valuation
within `season_end_date <= value_date <= season_end_date + 45 days`. This reproduces
the processed dataset's target rule without choosing a newer unrelated valuation.
No eligible observation produces null observation/difference for a player estimate.
Missing numeric season inputs produce 422 instead of inventing inputs.

## Simulator and persistence

```powershell
Invoke-RestMethod "$base/players/582/simulate" -Method Post -ContentType 'application/json' `
  -Body '{"goals":20,"assists":12}'
```

Only supplied fields override the stored season. Empty `{}` yields the same baseline
and simulation. Explicit numeric nulls are rejected; position null is allowed.
Both feature vectors are returned, and `difference_eur` here means **simulated
prediction minus baseline prediction**, rather than predicted minus observed.

Actual Haaland example: baseline 148951056 EUR, simulated 73917992 EUR, difference
-75033064 EUR. These tree-model outputs need not change smoothly or monotonically;
they do not establish causal effects of changing goals/assists. Stored seasons are
never edited by this endpoint.

Both POST endpoints default to `persist=false`. Add `?persist=true` (or
`&persist=true` alongside a season) to append one Prediction and receive its
`prediction_id`. Generic requests use a nullable player and `prediction_type=simulator`;
player simulations store only the simulated result, linked player and eligible
observed value. The exact validated model-input vector is stored as JSONB; numbers
are normalized to floats by validation, while original position text is retained.
The current registered ModelRun is linked, and raw outputs are converted using
the existing Decimal helper. Negative predictions persist unchanged.

GET requests never write predictions. POST retries with persistence intentionally
append separate history entries; there is no idempotency-key or deduplication API yet.
All persistence tests use isolated PostgreSQL test schemas, not development data.

## Ranking semantics

Rankings default to the latest stored season. One season query includes primary-club
and player information and one correctly dated observed value per row. Missing
observations or invalid numeric inputs are excluded and counted. Missing position
is supported. A single batch inference yields all eligible predictions.

`difference_eur = predicted_value_eur - observed_value_eur`.
Positive/negative endpoints include only their respective sign; zero differences
are omitted. Ties use ascending internal player ID. Fewer than `limit` rows can be
returned. `eligible_rows` counts the batch before sign filtering and `excluded_rows`
reports data eligibility exclusions. No prediction history is required or written.

Validated 2025/26 requests used 504 eligible rows, zero excluded:

| Direction | Player | Observed EUR | Predicted EUR | Difference EUR |
|---|---|---:|---:|---:|
| Largest positive | Igor Thiago | 65000000 | 94286296 | 29286296 |
| Most negative | William Saliba | 100000000 | 29618136 | -70381864 |

These are **model-estimated differences only**, not objective undervaluation or
overvaluation. This final model was trained on all five stored seasons, so these
rankings are descriptive model outputs on training observations, not unseen-season
evaluation evidence or investment recommendations.

## Money and model metrics

All public EUR fields use Pydantic `FiniteFloat` and JSON **numbers**, never formatted
currency strings. Observed PostgreSQL NUMERIC/Decimal values are consciously converted
to float at the response boundary for consistency with floating-point ML outputs.
This sacrifices arbitrary decimal precision in JSON; PostgreSQL history retains
exact Decimal values. No clipping or display rounding is performed. The frontend
will format currency. No confidence percentages are supplied.

`/models/current` returns V1 version 1.0.0, the five features, 2,594 training rows,
five training seasons and 2,103 temporal OOF evaluation rows. Stored metrics:

| Metric | Value |
|---|---:|
| Temporal OOF MAE EUR | 9677493.908571832 |
| Temporal OOF RMSE EUR | 15046414.97117625 |
| Temporal OOF R² | 0.5251604485345506 |
| Temporal OOF median absolute error EUR | 5881224.0 |

These are earlier expanding-window backtest results, **not test scores of the final
all-data fit**. The response retains this evaluation scope and known limitations.
`/models` lists only registered rows, currently V1; it invents no experimental
registrations. Neither endpoint returns artifact paths, credentials or raw metadata.

## Errors, tests and limits

Errors use `{"detail": ...}`: safe text for service errors, or a list of location/type/
message objects for validation errors. Input values are not echoed.

- 404: missing player/season, or no available ranking season.
- 422: missing/extra/invalid inputs, bad pagination, nonfinite values or unusable season inputs.
- 503: runtime model/inference or database dependency failure.
- 500: unexpected server failure; no stack trace is returned.

Startup failures stop the process before serving. Logs identify failure categories
and model identity without logging connection strings, input bodies or secrets.
Health performs `SELECT 1` and checks loaded model presence; it does not rerun a full
prediction on every health request. CORS permits configured browser origins only.

```powershell
. ./.local/database-env.ps1  # sets separate TEST_DATABASE_URL on this workstation
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
```

API tests reuse Session 10's random-schema migration fixture exclusively through
TEST_DATABASE_URL. Focused tests inject a deterministic model; one integration test
loads the real frozen V1 artifact and verifies the actual prediction and metrics.
No test retrains a model. PostgreSQL tests skip explicitly when their test URL is
absent; the real-model test also skips if the local artifact is unavailable.

Session 11 validation: 216 tests passed (31 new API tests), Ruff lint/format and
dependency checks passed, ten OpenAPI paths generated, and live Uvicorn requests
against the real local PostgreSQL database succeeded. All 116 snapshotted frozen
files remained unchanged, with no Alembic drift. Development table counts stayed
1,139 players, 27 clubs, 2,594 seasons, 2,594 values, one model and zero predictions.

Remaining limits: local single-service validation only; no auth, rate limiting,
deployment, shared caching or background jobs. Rankings recompute each request and
are suitable for this small EPL dataset. Position history, target coverage and
source accuracy limitations remain those of V1. Full player-history pagination,
future-provider target policies and production operational hardening are future work.

## Files for this milestone

Created: `backend/app/main.py`, `dependencies.py`, `routes.py`, `schemas.py`;
`backend/app/core/__init__.py`, `config.py`, `errors.py`;
`backend/app/services/__init__.py`, `model_service.py`, `player_service.py`,
`prediction_service.py`, `ranking_service.py`; `backend/tests/test_api.py`; this document.
Updated: `.env.example`, `pyproject.toml`, `requirements-dev.txt`, root `README.md`.
Existing DB code, import logic, migration 0001, ML code, raw/processed data, model
artifacts and evaluation files remain unchanged.
