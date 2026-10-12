# Session 14 — Model Lab

`/models` now explains how PlayerWorth progressed from a linear baseline to the
frozen position-aware XGBoost V1. No retraining, new experiment, backend endpoint,
schema change, deployment or final palette redesign was performed.

## Page composition

- Intro and live current-model registry card.
- Six-stage evolution: Linear Regression, Ridge, Random Forest, four-feature
  XGBoost, position, then temporal validation.
- Exploratory 2025/26 comparison table with five models, feature counts, MAE,
  RMSE, R² and outcomes. Compact explanations define each metric.
- Four expanding-window fold tracks, separate pooled OOF results and the caveats
  that make these retrospective rather than fully independent model selection.
- Accepted position feature (MAE improved in 4/4 folds) beside rejected goals/90
  and assists/90 (MAE worsened in 4/4 folds).
- A complete 13-feature normalized gain chart and summed position-family gain.
- Visible limitations, current API limitations and expandable source provenance.

## Sources and protocol separation

The server route uses the existing typed `getCurrentModel()` and `getModels()`
methods concurrently. Both are read-only and uncached. Current identity, version,
feature list, counts, evaluation description, live MAE/R² and limitations come
from those responses. Only one model version is currently registered. The history
does not pretend the experimental models are registered API models. Each API
failure is handled independently; frozen history stays readable during an outage.

`frontend/lib/model-history.ts` is a strongly typed, committed frontend snapshot
of these existing local artifacts:

| Source artifact | Contents copied |
| --- | --- |
| `ml/models/model_metrics.json` | Five exploratory holdout comparisons, full numerical precision |
| `ml/evaluation/temporal_backtest_summary.json` | Folds, sample sizes, position deltas and pooled position results |
| `ml/evaluation/per90_backtest_summary.json` | Pooled rejected per-90 results |
| `ml/models/playerworth_v1_feature_importance.json` | All 13 final-fit gain values and position-family total |

The snapshot records source filenames and SHA-256 hashes. It does not copy live
registry identity. The page builds without reaching outside the frontend or needing
ignored ML artifacts on the deployment filesystem. When deliberately updating
historical evidence, verify the replacement artifacts, copy their measured values,
update source hashes and revalidate the narrative. Do not silently regenerate or
train models during a frontend build.

Narrative sources are MODEL_CARD_V1.md, LINEAR_REGRESSION.md, RIDGE_REGRESSION.md,
RANDOM_FOREST.md, XGBOOST.md, POSITION_FEATURE.md and TEMPORAL_BACKTESTING.md.
The older Linear Regression report contains an inconsistent R² in its prose/main
table. This page uses the frozen JSON and model-card value **0.4528572436193363**,
matching the requested Session 14 comparison. The protected historical documents
and artifacts were not rewritten to resolve that older prose discrepancy.

The comparison table is explicitly **exploratory 2025/26 held-out-season** evidence:
2,090 earlier-season training rows and 504 evaluation rows. Repeated inspection
and differing selection procedures preclude calling it an untouched final leaderboard.

Temporal evaluation is a separate section:

| Train | Test | Train rows | Test rows |
| --- | --- | ---: | ---: |
| 2021/22 | 2022/23 | 491 | 522 |
| 2021/22–2022/23 | 2023/24 | 1,013 | 534 |
| 2021/22–2023/24 | 2024/25 | 1,547 | 543 |
| 2021/22–2024/25 | 2025/26 | 2,090 | 504 |

Position-model pooled OOF evidence: **MAE €9,677,493.91**, **RMSE €15,046,414.97**,
**R² 0.525160448535**, **median absolute error €5,881,224**, from 2,103 predictions.
These are pooled errors, not averages of fold scores and not final all-data-fit
test performance. Frozen settings originally selected using 2024/25 limit the
historical independence of earlier folds. Overlap, repeated players and lack of
significance testing are stated on the page.

Per-90 pooled MAE is €9,749,592.38, worse than the position baseline. Gain importance
comes from the final all-data fit, not a fold fit. Position-family normalized gain
is 0.2977507319301367. It measures split usefulness, not causation, a coefficient or
the fraction of market value caused by position. R² is never presented as accuracy.

## Charts, accessibility and theme

The fold visualization uses labeled Train/Test/unused cells with no animation
dependency. The gain chart uses responsive HTML/CSS bars with all numeric labels
in an ordered list and a figure caption. This is sufficient for a small fixed
dataset and adds no new chart dependency or client JavaScript.

`components/ui/analytics.css` centralizes `--chart-primary`, `--chart-secondary`,
`--chart-grid`, `--chart-track` and `--analytics-emphasis` roles. They reference
existing global tokens; no new lime or other hardcoded color values were added.
Future recoloring can change these roles without altering data or components.

The desktop timeline stacks vertically on mobile. The comparison table scrolls
only inside its labeled, keyboard-focusable region. Fold tracks fit phone widths;
the gain chart keeps every feature and value readable. Metadata describes the
project's model-building process without claiming objective true valuations.

## Validation, 6 October 2026

PostgreSQL, FastAPI and the production Next.js server ran locally. The API reported
`playerworth_v1`, version `1.0.0`, 2,594 final training rows and 2,103 OOF predictions.

- Frontend lint, TypeScript typecheck and Next.js production build passed.
- 57 frontend unit/component tests passed, including history/protocols, all stages,
  live registry values, API outage fallback, gains, metrics and limitations.
- 10 live desktop/mobile browser tests passed across the app. Model Lab checks
  current API data, six stages, four folds, pooled metrics, per-90 rejection,
  complete importance and limitations. Existing profile/simulator coverage passed.
- Existing Python suite: 216 passed, using the separate configured test database.
- Browser checks reported no console/page errors in successful flows, and no
  page-level horizontal overflow at 320, 390, 768, 1280 and 1440-pixel widths.
- Desktop/full-page and focused mobile screenshots were visually inspected.
- All 136 protected backend/ML/data/evaluation files retained their SHA-256 hashes.

On 7 October, the existing local services were restarted after they had stopped
between sessions. Fresh complete loads of `/models` and `/rankings` returned HTTP
200 with no browser errors or new server warnings. An earlier automated-navigation
log contained three destination-stream-closed messages; these did not recur in
the complete-load check.

Run from `frontend/`: `npm run lint`, `npm run typecheck`, `npm run test`,
`npm run build`, then `npm run test:e2e` with the local services running.
From the repo root, run `.venv\Scripts\python.exe -m pytest -q` with the configured
test database environment. Local screenshots/logs remain ignored under `.local/`.

## Session 14 file inventory

Created:

- `frontend/lib/model-history.ts`: typed verified frozen evidence and provenance.
- `frontend/components/model/ModelLab.tsx`: research narrative, metrics and folds.
- `frontend/components/model/ImportanceChart.tsx`: accessible gain bars.
- `frontend/app/models/loading.tsx`: loading shell.
- `frontend/lib/rankings.ts`: known cohort seasons, query parsing and validation.
- `frontend/components/rankings/RankingsExplorer.tsx`: selected-list requests/state.
- `frontend/components/rankings/RankingsTable.tsx`: desktop rows/mobile cards.
- `frontend/app/rankings/loading.tsx`: loading shell.
- `frontend/components/ui/analytics.css`: scoped shared Session 14 styles/tokens.
- `frontend/tests/model-lab.test.tsx`, `frontend/tests/rankings.test.tsx`: synthetic tests.
- `frontend/e2e/analytics.spec.ts`: live integration and responsive checks.
- `docs/MODEL_LAB.md`, `docs/RANKINGS_UI.md`: feature guides.

Modified:

- `frontend/app/models/page.tsx`: replaces placeholder with server-fetched Model Lab.
- `frontend/app/rankings/page.tsx`: replaces placeholder with query-aware rankings.
- `frontend/lib/api/client.ts`: optional abort signals on existing ranking methods.
- `frontend/e2e/home.spec.ts`: completed-route navigation replaces placeholder check.
- `README.md`: links and milestone status.

No dependency changes were needed. Homepage and profile implementation files were
not changed. Session 15, final branding and deployment remain unstarted.

## Remaining limitations

Frozen history needs deliberate maintenance if accepted evidence changes. Current
registry metrics may evolve independently and remain labeled separately. No actual
versus predicted scatter was invented because the API does not expose evaluation
points. No statistical significance or future-performance guarantee is claimed.
Live browser testing used Chromium desktop/mobile emulation, not every engine.
The pre-existing development-only ESLint dependency advisory remains outside this
milestone; no forced dependency downgrade was performed.
