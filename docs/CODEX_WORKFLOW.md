# Codex Workflow

This file explains how Codex should work on PlayerWorth.

## Core Principle

Do not ask Codex to "build the entire app."

Use Codex as an engineering partner for one milestone at a time.

## Before Every Task

Codex should:

1. read the root README
2. read the relevant section README
3. inspect existing code
4. summarize the intended change
5. identify files it expects to modify
6. preserve existing interfaces unless change is required

## Scope Discipline

For each request:

- modify only necessary files
- avoid unrelated refactors
- do not add speculative features
- do not replace working code just because another style is preferred
- do not silently change dependencies
- add tests with functionality

## Suggested Session Order

### Session 1 — Repo Skeleton

Prompt:

```text
Read README.md.

Create the repository directory structure only.

Add basic Python and Next.js project configuration where necessary, but do not build product features yet.

Afterward, explain the structure and list the next milestone.
```

### Session 2 — Data

Use the prompt at the bottom of `DATA_README.md`.

### Session 3 — Linear Regression

Use the prompt at the bottom of `ML_README.md`.

After it works, ask:

```text
Explain the Linear Regression implementation to me as a computer science student learning ML.

Explain:
- X
- y
- train/test split
- preprocessing
- coefficients
- MAE
- RMSE
- R²

Use the actual code in this repository.
Do not modify files.
```

This is important: understand the model before moving on.

### Session 4 — Better Models

Prompt:

```text
Read docs/ML_README.md and inspect the current Linear Regression pipeline.

Add Ridge Regression only.
Evaluate it using the exact same split and metrics as Linear Regression.
Update model_metrics.json generation and tests.

Do not add Random Forest or XGBoost yet.
```

Then repeat separately for Random Forest and XGBoost.

### Session 5 — Database

Use `DATABASE_README.md`.

### Session 6 — Backend

Use `BACKEND_README.md`.

### Session 7 — Frontend Foundation

Use `FRONTEND_README.md`.

### Session 8 — Player Page

Prompt:

```text
Read docs/FRONTEND_README.md and inspect the existing frontend/backend contracts.

Build the player detail page using real backend data.

Include:
- player header
- observed market value
- predicted market value
- value difference
- season stats
- per-90 stats

Do not build the simulator in this task.
Add loading/error/empty states.
```

### Session 9 — Transfer Simulator

Prompt:

```text
Build the PlayerWorth Transfer Simulator using the existing prediction API.

Requirements:
- begin from a real player's current feature values
- editable controls for supported features
- debounce prediction requests
- clearly show original vs simulated prediction
- show the EUR difference
- include a disclaimer that this is a hypothetical model output
- handle API loading/errors
- do not invent confidence scores

Add tests.
```

### Session 10 — Model Lab

Prompt:

```text
Build the Model Lab page using real backend model metrics.

Show:
- Linear Regression
- Ridge
- Random Forest
- XGBoost
- MAE
- RMSE
- R²

Add an actual-vs-predicted chart only if the backend exposes real evaluation points.
Do not fabricate chart values.

For linear models, display coefficient data if the API exposes it.
```

### Session 11 — Rankings

Prompt:

```text
Build undervalued and overvalued ranking views using the backend ranking endpoints.

Sort using:
predicted_value_eur - observed_value_eur

Use wording such as "model-estimated difference."
Do not state that a player is objectively overvalued or undervalued.
```

### Session 12 — Testing and Deployment

Use `TESTING_README.md`, then `DEPLOYMENT_README.md`.

## Best Prompt Pattern

Use:

```text
Read:
- README.md
- <relevant README>

Goal:
<one concrete milestone>

Requirements:
<exact behavior>

Constraints:
<what NOT to change>

Before coding:
1. inspect the relevant current files
2. state the implementation plan
3. mention any assumptions

Then implement, test, and summarize changed files.
```

## When Codex Produces Something You Do Not Understand

Do not continue.

Ask:

```text
Do not change any code.

Teach me what you just implemented.
Walk through the important files and explain why each piece exists.
Assume I am learning this concept.
```

## Git Workflow

Prefer one logical commit per milestone.

Example:

```text
feat(data): build player dataset pipeline
feat(ml): add linear regression baseline
feat(ml): add ridge comparison
feat(api): add prediction endpoint
feat(web): add player profile
feat(web): add transfer simulator
```

## Final Rule

PlayerWorth is an ML learning project first and an AI-assisted coding project second.

Codex can write significant code, but the developer should understand:

- what data enters the model
- what the target is
- why preprocessing exists
- what each metric means
- why models differ
- how the model reaches production inference
