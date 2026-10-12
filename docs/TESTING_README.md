# Testing

## Goal

Protect the most important parts of PlayerWorth:

- data correctness
- ML reproducibility
- inference correctness
- API contracts
- frontend critical flows

## Data Tests

Test:

- position normalization
- name normalization
- per-90 calculations
- duplicate handling
- invalid minutes
- market-value parsing
- merge behavior

Use tiny fixtures created only for tests.

## ML Tests

Test:

- preprocessing accepts expected columns
- unknown categorical values do not crash inference
- zero-minute feature engineering
- prediction returns finite number
- serialized pipeline reloads successfully
- transformed target is correctly inverted
- training with fixed seed is repeatable where supported

Do not assert exact performance metrics on tiny test fixtures.

## Backend Tests

Use pytest.

Test:

- health endpoint
- request validation
- missing required features
- invalid values
- successful prediction
- player not found
- database service behavior
- ranking sort order
- model unavailable behavior

## Frontend Tests

Use the project-standard React testing stack selected during setup.

Test:

- search state
- prediction response rendering
- simulator input behavior
- metric rendering
- error state
- loading state

## End-to-End

Critical E2E journey:

1. open homepage
2. search for player
3. open player
4. see predicted/observed values
5. change simulator input
6. receive updated prediction
7. open Model Lab

Use Playwright if appropriate.

## CI

GitHub Actions should eventually run:

```text
python formatting/lint
python tests
frontend lint
frontend typecheck
frontend tests
build
```

E2E can run separately if infrastructure is required.

## Acceptance Criteria

- critical Python logic covered
- API happy/error paths covered
- TypeScript typecheck passes
- frontend critical states tested
- no production deployment when CI is red

## First Codex Prompt

```text
Read README.md and docs/TESTING_README.md.

Inspect the existing repository and add tests only for code that already exists.

Prioritize:
1. feature engineering
2. model inference
3. prediction API
4. typed frontend API interactions

Do not introduce major new product features while writing tests.
```
