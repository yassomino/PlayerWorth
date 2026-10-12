# Backend API

## Goal

Build the FastAPI service connecting:

- frontend
- PostgreSQL
- trained ML pipelines

## Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   └── logging.py
│   ├── db/
│   ├── schemas/
│   ├── routes/
│   │   ├── health.py
│   │   ├── players.py
│   │   ├── predictions.py
│   │   ├── rankings.py
│   │   └── models.py
│   └── services/
│       ├── player_service.py
│       ├── prediction_service.py
│       └── model_service.py
└── tests/
```

## Rules

- Pydantic request/response schemas
- type hints
- no model training inside requests
- load production model once on startup
- service layer owns business logic
- API routes stay thin
- clear validation errors
- structured logging
- CORS configured through environment
- use `/api/v1`

## Required Endpoints

### Health

```http
GET /api/v1/health
```

```json
{"status":"ok"}
```

### Player Search

```http
GET /api/v1/players?search=saka
```

Return compact player results.

### Player Detail

```http
GET /api/v1/players/{player_id}
```

Return:

- player info
- season stats
- observed market value
- production prediction
- model name/version

### Prediction

```http
POST /api/v1/predictions
```

Example request:

```json
{
  "age": 23,
  "position": "W",
  "minutes": 2900,
  "goals": 15,
  "assists": 12
}
```

Example response:

```json
{
  "model_name": "linear_regression",
  "model_version": "v1",
  "predicted_value_eur": 126400000
}
```

### Player Simulator

Optional convenience endpoint:

```http
POST /api/v1/players/{player_id}/simulate
```

The backend loads the player's existing feature vector, applies only allowed changes, then predicts again.

### Model Metrics

```http
GET /api/v1/models
GET /api/v1/models/{model_name}
```

Return real recorded metrics.

### Rankings

```http
GET /api/v1/rankings/undervalued
GET /api/v1/rankings/overvalued
```

Use:

```text
prediction_difference =
predicted_value_eur - observed_value_eur
```

## Prediction Service

Responsibilities:

1. validate incoming feature schema
2. load selected pipeline
3. convert request into model input
4. call `.predict()`
5. reverse target transform if required
6. return normalized EUR number

The API must not manually reproduce preprocessing logic that already exists in the saved pipeline.

## Model Loading

Configuration:

```text
MODEL_PATH=
MODEL_NAME=
MODEL_VERSION=
```

Fail loudly at startup if the configured production model cannot load.

## Error Handling

Examples:

- 404 player not found
- 422 invalid prediction input
- 503 production model unavailable

Do not expose server stack traces to clients.

## Acceptance Criteria

- API starts locally
- `/health` works
- model loads once
- prediction endpoint returns real model output
- player routes query DB
- ranking routes work
- model metrics come from stored training results
- tests cover validation and inference
- OpenAPI docs are usable

## First Codex Prompt

```text
Read README.md, docs/ML_README.md, docs/DATABASE_README.md, and docs/BACKEND_README.md.

Implement only the backend foundation:
1. FastAPI app
2. config
3. health endpoint
4. production-model loader
5. POST /api/v1/predictions
6. Pydantic schemas
7. prediction service
8. tests

Do not build player search or rankings yet.
Use the saved scikit-learn pipeline directly.
```
