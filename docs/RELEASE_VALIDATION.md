# Session 15 release validation

Validated locally on Windows, 12 October 2026. **V1 application complete /
deployment configuration complete; not live deployed.**

## Results

| Check | Result |
|---|---|
| Full Python suite with PostgreSQL integration | 218 passed |
| Ruff lint / formatting | Passed for backend, ML, scripts and tests |
| Frontend ESLint / TypeScript | Passed |
| Frontend Vitest | 60 passed across 9 files |
| Optimized Next.js build | Passed; all four product routes built |
| Full configured Playwright suite | 37 passed; 2 duplicate width sweeps intentionally skipped |
| Chromium desktop / mobile | Passed |
| WebKit | Passed including search, profile, simulator and rankings |
| Firefox | Binary installed; Windows launch fails with `spawn UNKNOWN`; not validated |
| axe WCAG 2 A/AA and 2.1 AA checks | No violations on loaded home, open search, profile, Model Lab, rankings and 404 |
| Responsive matrix | All four product routes fit 320/360/390/430/768/1024/1280/1440/1920/2560px |
| Runtime npm audit | 0 vulnerabilities |
| Full npm audit | 5 high dev-dependency entries in the Next ESLint glob/braces chain remain |
| Protected SHA-256 comparison | 136/136 files unchanged |
| Private backend release bundle | 54 allowlisted files, copied hashes verified |
| Docker build / hosted deployment | Not run: Docker unavailable; provider authentication not configured |

The full audit's proposed automatic fix downgrades `eslint-config-next` to 14.2.35,
incompatible with the deliberate Next 16 setup. No forced major downgrade was
applied. These are development-tool dependencies, not runtime packages; keep the
issue visible for a compatible upstream fix.

The full browser suite uses one worker for consistent local service load. Firefox
can be attempted explicitly with `TEST_FIREFOX=1`; it is not silently claimed as
passing. WebKit initially exposed an input-before-hydration race. Search now remains
disabled until its controlled input can handle events, with a server-rendering
regression test. Final browser flows passed without captured console/page errors.

The final continuation also checks the open search dropdown. Its result anchors
now carry the option role directly, avoiding nested interactive elements while
preserving pointer navigation and the combobox's arrow-key/Enter behavior.
The homepage smoke flow uses visible footer links and waits for destination
content, rather than interrupting Next.js prefetch requests with immediate hard
document navigations; console errors remain asserted, not filtered out.

## Visual and interaction checks

Before/after desktop and mobile screenshots were inspected for all four routes.
Additional narrow, tablet and ultrawide captures were inspected. The 320px audit
led to two-column profile statistics and stacked homepage metrics; values must not
collide even when the document itself reports no horizontal overflow. Responsive
and accessibility checks were rerun after those changes. Seven final portfolio
captures are stored in `docs/screenshots`; raw debug images remain ignored.

Verified search → discovered Haaland profile, recorded history/table, season
selection, simulator update/reset, Model Lab content, rankings season/direction and
profile navigation, missing-player recovery, unknown-route recovery and mobile
Escape/focus behavior. Unit coverage also exercises API errors, empty states,
stale requests, invalid inputs and rejected ranking query state. New error-boundary
tests verify retry and that internal error text is not displayed. The root favicon
and metadata now reflect the original PW identity.

Chart ARIA grouping, focus indicators, readable contrast, reduced motion and signed
textual value differences were reviewed. Automated accessibility checks do not
constitute a complete screen-reader or real-device certification. Horizontally
scrollable data tables stay inside their own regions.

## Data and behavior preserved

SHA-256 checks cover the pre-existing ML code, raw/processed data, trained artifacts,
evaluation files, backend code/tests and migration `0001`. All 136 recorded files
remain byte-identical. No model was trained, feature added, dataset rebuilt,
endpoint changed or schema migrated to a new version.

The staged release itself successfully imports and loads V1 and returns the
expected €82,459,040 frozen smoke estimate using the local Python runtime. This
does not substitute for the pending Linux container build. Local CORS preflight
allows exactly `http://localhost:3000` (200) and rejects an unrelated origin (400,
no allow-origin header); hosted CORS still requires the actual provider URL.

Two local seed runs left counts unchanged: 1,139 players, 27 clubs, 2,594 seasons,
2,594 valuations, one model run and **zero predictions**, including after browser
simulator/ranking checks. Haaland's stored 2025/26 input still returns
€148,951,056; changing goals to 20 and assists to 12 returns €73,917,992 without
persisting a prediction. These are functional smoke outputs, not evaluation scores.

There is no `.git` directory in this workspace, so no commit or Git diff could be
produced. Existing `.gitignore` rules continue to exclude raw CSVs, generated
artifacts and local secrets; `.dockerignore` independently allowlists image content.

## Files changed or added

| Files | Purpose |
|---|---|
| `frontend/app/globals.css` | Central palette, shell, home, mobile metrics, focus and motion |
| `frontend/components/player/profile.css` | Profile, chart, simulator and narrow stat layout |
| `frontend/components/ui/analytics.css` | Model Lab and rankings styles |
| `frontend/components/layout/Navbar.tsx`, `Footer.tsx` | PW identity, Home navigation, mobile keyboard recovery, footer links |
| `frontend/components/home/Hero.tsx` | Final product wording and original pitch treatment |
| `frontend/components/search/PlayerSearch.tsx` | Search wording and hydration-safe input |
| `frontend/components/player/ValuationHistory.tsx` | Valid named chart group and safe initial chart width |
| `frontend/app/layout.tsx`, `icon.svg` | Open Graph basics and original app mark |
| `frontend/app/error.tsx`, `not-found.tsx` | Safe retry and route recovery |
| `frontend/e2e/accessibility.spec.ts` | Loaded-page axe, focus and viewport matrix |
| `frontend/e2e/home.spec.ts`, `profile.spec.ts` | Updated heading and accessible search-option expectations |
| `frontend/playwright.config.ts` | WebKit, optional Firefox, configurable hosted base URL |
| `frontend/tests/shell.test.tsx`, `search.test.tsx` | Error/404 and hydration regression tests |
| `frontend/package.json`, `package-lock.json` | axe development dependency |
| `frontend/vercel.json` | Next.js deployment configuration |
| `Dockerfile`, `.dockerignore`, `railway.json`, `requirements-runtime.txt` | Allowlisted non-root backend image, PORT binding and dependency health check |
| `scripts/prepare_release.py`, `tests/test_release.py`, `pyproject.toml` | Verified release staging and tests |
| `README.md` | Portfolio overview, real evidence, architecture, setup and screenshots |
| `docs/FRONTEND_README.md` | Current V1 status alongside the original plan |
| `docs/BRAND_AND_DESIGN.md` | Design system and page rules |
| `docs/DEPLOYMENT.md` | Provider configuration, exact commands, TLS/CORS, seed and rollback |
| `docs/RELEASE_VALIDATION.md` | This evidence and change inventory |
| `docs/screenshots/*.png` (7 files) | Home/player desktop and mobile, Model Lab, rankings, simulator |

## Hosting status and next operational action

Supabase: no project connected, hosted migrations/seeding not run.
Railway: no service deployed, container build not executed here.
Vercel: no public frontend deployment.
No live URL or production smoke result exists. Authentication and Docker/container
validation are required to execute the documented release steps. The checked
bundle is `.local/release-v1-final`; it contains neither credentials nor raw exports.

The recommended Vercel → Railway → Supabase chain is configuration-ready. Follow
[DEPLOYMENT.md](DEPLOYMENT.md) after signing in, then verify health, model identity,
database counts, exact-origin CORS and the complete browser flow at provider URLs.
Data licensing/provenance, snapshot position and model uncertainty remain the
limitations documented in the frozen model card. No V2 work was started.


