# Session 13 — Player profile and Transfer Simulator

The profile is implemented at `/players/[id]`. IDs are internal database IDs
returned by search, not Transfermarkt IDs and not constants across installations.
Model Lab and full Rankings remain future work. Backend behavior, database schema,
ML artifacts and model configuration are unchanged.

## Page and data flow

The server route fetches `GET /api/v1/players/{id}` through the existing typed
client. React request caching shares this lookup with dynamic metadata. The name
and description are populated without embedding a potentially stale estimate.

The profile contains an initials portrait and selected-season club/age/position,
a valuation hero, prominent appearance/minutes/goals/assists statistics, a separate
five-input model panel, recorded market-value history, the simulator and a
newest-first season table. Nationality is shown only when available. Club means
primary club for the stored season, not guaranteed current membership. Per-90
and card statistics are descriptive and are not sent to the model.

Latest stored season is the default. The select and season-table buttons share
state and update `?season=2024%2F25` through browser history without a full page
reload. Refresh and browser Back restore the selection. An unavailable explicit
season is reported rather than silently replaced. Season changes remount the
prediction/simulator state and cancel the previous request. Late responses cannot
overwrite the new season. History remains sourced from the original detail payload.

## Prediction semantics

`GET /players/{id}/prediction?season=...` supplies the estimate, observed value,
five baseline inputs and model identity. The hero uses the API's difference:

```text
model difference = predicted_value_eur - observed_value_eur
```

Signed amounts have above/below/equal text, not color alone. Missing observations
are unavailable, never zero. Model outputs are not true transfer values or proof
of objective undervaluation. The frozen V1 was refitted on the full dataset;
these profile predictions are descriptive, not new held-out evaluation results.

## Historical values

Recharts renders only real `market_values` supplied by the API, ordered by date.
Markers represent stored observations; connecting lines do not create additional
valuations. Tokens style axes, grid and tooltip. The tooltip shows date, full EUR
amount and source. A textual summary and expandable data table provide accessible
alternatives. Empty histories display an explicit empty state.

The season table aligns existing observations for display using the same current
API policy: earliest Transfermarkt valuation between season end and +45 days,
inclusive. It never fills missing values or requests predictions for every row.
This small display helper has boundary tests and must stay aligned if the API's
documented observation policy changes. The hero always uses the API response.

## Simulator

Controls use the selected prediction's actual five inputs: age, minutes, goals,
assists and position. Four sliders are paired with number inputs; standard slider
maxima are 45, 4,500, 50 and 30, expanding for larger entered/stored values. Manual
entry is not capped to these ranges. Inputs must be finite and nonnegative;
goals/assists must be integers. Position offers GK, CB, FB, DM, CM, AM, W and ST;
an existing unmapped value is preserved only when present in the stored baseline.

The explicit **Update estimate** button sends only changed fields to
`POST /players/{id}/simulate?season=...`. No request is sent per keystroke. No
persist flag is enabled, so the API default `persist=false` applies. No model
prediction is calculated in JavaScript, and no original season data is mutated.

The output displays the baseline, returned simulation and API-provided difference:

```text
simulation change = simulated prediction - baseline prediction
```

Editing cancels an outstanding request and invalidates its result. Reset cancels
the request, restores all five original inputs and immediately restores the known
baseline without another POST. Changing season starts a fresh simulator.

A visible warning explains that responses are hypothetical, non-causal and not
necessarily monotonic. More goals or assists need not increase an estimate.

## Loading, errors and responsive behavior

The route provides structured header/value/stats/chart/simulator skeletons.
Prediction loading is localized so statistics remain usable. Prediction failure
shows a retry action and prevents simulation until a baseline exists. Simulation
failure preserves the original estimate and editable inputs. A missing player has
a dedicated 404 state and a Back to PlayerWorth link; other profile fetch failures
show a safe recovery screen, not raw API details.

Mobile layouts stack the value hero, model panel, controls and scenario result.
Season history scrolls within its own focusable region; the page does not overflow.
Inputs have labels and associated validation messages, with visible keyboard focus.

## Themeability

New components use existing surface, text, border and difference tokens. Profile
aliases `--profile-chart`, `--profile-control` and `--profile-emphasis` currently
resolve to foreground, not lime. Their color roles can be changed centrally in
`components/player/profile.css`; layout and interaction do not depend on the
temporary Session 12 palette. No PL assets, logos, player photos or scraped content
were introduced. A permanent brand redesign remains separate work.

## Verified local example

On 6 October 2026, search returned Haaland's local internal ID 582. Browser tests
discover this ID from search rather than assuming it. Four stored seasons and four
recorded valuations are available for this player.

| 2025/26 result | EUR |
| --- | ---: |
| Baseline: age 25, minutes 2,959, goals 27, assists 8, ST | 148,951,056 |
| Observed value | 200,000,000 |
| Model minus observed | -51,048,944 |
| Scenario: goals 20, assists 12; other inputs unchanged | 73,917,992 |
| Scenario minus baseline | -75,033,064 |

The decreasing scenario is shown exactly as returned, without frontend correction.
The response has `prediction_id: null`. Reset restores 27 goals, 8 assists and the
original estimate. Switching to 2024/25 restores 22 goals, 3 assists, 2,743 minutes
and age 24; this selection survives refresh.

## Validation

With PostgreSQL, FastAPI and the frontend running, from `frontend/`:

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

Results: lint, typecheck and production build passed; **42 frontend unit tests**
and **6 live browser tests** passed. Desktop Chromium and mobile Chromium with
iPhone 13 viewport exercised homepage search, profile, chart, observed/baseline
values, scenario submission, reset, season change, refresh, Back and missing-player
recovery. Successful profile flows emitted no console/page errors and no document
horizontal overflow. Desktop/mobile full-page screenshots were visually reviewed.
Screenshots and local server logs remain ignored under `.local/`.

The existing Python suite passed **216 tests**, using the configured separate test
database. SHA-256 comparison verified **136 backend/ML/data files unchanged**.
Synthetic component tests cover all five overrides, explicit partial submissions,
unchanged original data, reset, stale prediction/simulation cancellation, errors,
missing observations, chart ordering/empty state and historical date boundaries.
The API-client test verifies the POST body and absence of enabled persistence.

## File inventory

Created:

- `frontend/app/players/[id]/loading.tsx` — structured loading state.
- `frontend/app/players/[id]/not-found.tsx` — player recovery state.
- `frontend/components/player/PlayerProfile.tsx` — synchronized season state.
- `frontend/components/player/PlayerHeader.tsx` — real identity and season context.
- `frontend/components/player/SeasonEstimate.tsx` — cancellable prediction and errors.
- `frontend/components/player/SeasonStats.tsx` — descriptive football statistics.
- `frontend/components/player/ModelInputs.tsx` — exactly five V1 inputs.
- `frontend/components/player/ValuationHistory.tsx` — chart and accessible records.
- `frontend/components/player/SeasonHistory.tsx` — selectable season table.
- `frontend/components/player/ValueDelta.tsx` — signed, explained differences.
- `frontend/components/player/profile.css` — responsive, token-based styling.
- `frontend/components/simulator/TransferSimulator.tsx` — unsaved scenario controls.
- `frontend/lib/player.ts` — sorting, display alignment, input validation/overrides.
- `frontend/tests/player-profile.test.tsx` — synthetic component/helper coverage.
- `frontend/e2e/profile.spec.ts` — live desktop/mobile profile coverage.
- `docs/PLAYER_PROFILE.md` — this guide.

Modified:

- `frontend/app/players/[id]/page.tsx` — real profile route and dynamic metadata.
- `frontend/lib/api/client.ts` — optional abort signals for prediction/simulation.
- `frontend/lib/format.ts` — shared date and number formatting.
- `frontend/components/ui/RouteShell.tsx` — optional recovery-link label.
- `frontend/tests/api.test.ts` — unsaved simulation request coverage.
- `frontend/e2e/home.spec.ts` — returned-ID navigation to the completed profile.
- `frontend/package.json`, `frontend/package-lock.json` — Recharts dependency.
- `README.md`, `docs/FRONTEND_FOUNDATION.md` — current milestone links/status.

## Remaining limits

Valuation history is the stored snapshot, not a complete daily/live time series.
Position is snapshot metadata, not independently verified historical position.
Realistic-looking scenarios can be outside training support; validation guarantees
basic input validity, not football plausibility or reliable extrapolation. No
confidence intervals or causal interpretations are supplied. Observations can be
missing. Images remain initials. Local tests cover Chromium, not all browser engines.
The existing Session 12 development-only ESLint dependency advisory remains; no
forced lint-tool downgrade was introduced. No Session 14 work or deployment was done.
