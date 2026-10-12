# Session 12 — Frontend foundation and homepage

The Next.js App Router homepage consumes the unchanged Session 11 API. Player
profiles, Model Lab and rankings have navigation shells only. No simulator,
prediction persistence controls, authentication or deployment was added.

## Local setup

Use three terminals: PostgreSQL, FastAPI and Next.js. Follow DATABASE.md for Docker
or the existing portable PostgreSQL instance. For the latter on this workstation:

```powershell
$pgRoot = Join-Path $env:LOCALAPPDATA 'PlayerWorth'
& "$pgRoot\pgsql\bin\pg_ctl.exe" -D "$pgRoot\data" -l "$pgRoot\postgres.log" start
```

From the repository root, start the backend using its existing configuration:

```powershell
. ./.local/database-env.ps1
.venv\Scripts\python.exe -m backend.app.main
```

Then start the frontend:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local # first setup only; do not overwrite personal settings
npm run dev -- --hostname localhost
```

Open **http://localhost:3000**. `NEXT_PUBLIC_API_BASE_URL` must include `/api/v1`;
the example uses `http://127.0.0.1:8000/api/v1`. The browser origin is localhost:3000,
which matches the API's existing default CORS configuration. Do not switch the
frontend browser host to 127.0.0.1 without configuring the allowed origin yourself.
No backend changes were required. `.env.local` is ignored, while the example is
tracked. Rebuild after changing public environment variables for production builds.

## Design and page structure

Charcoal/olive surfaces, lime highlights and warm negative-value accents form a
football-first visual system. Inter supports compact information; locally hosted
Barlow Condensed supports large headings and tabular-value displays. CSS variables
define backgrounds, surfaces, borders, text, accent, signed values, focus, radius
and base spacing. Tailwind 4 is configured for shared utilities and tokens.
The pitch is decorative CSS, not a data visualization or invented player formation.
No photos, scraped images, fake badges or corporate logo assets are used.

The homepage contains:

1. Search-led hero and decorative pitch graphic.
2. Current V1 model snapshot with explicitly labeled temporal OOF metrics.
3. Two live three-player ranking previews and a visible interpretation disclaimer.
4. Three-step explanation: performance, model and estimate.
5. Concise model-development progression and Model Lab link.
6. Shared navigation and footer.

Server components render the static content and independently fetch each model or
ranking section. Suspense supplies section skeletons. Failed fetches produce local
fallbacks rather than crashing the homepage. The entire page is not a client component.
Only autocomplete and the mobile navigation need client state. No React Query/SWR,
charting library, UI framework or icon package was needed for this scope.

## API and interaction contracts

`lib/api/types.ts` mirrors `backend/app/schemas.py`: player summaries/details/seasons,
observations, inputs, predictions, simulations, registered/current models and rankings.
`lib/api/client.ts` centralizes GET/POST functions, environment configuration, query
encoding, safe HTTP/network errors, no-store fetching and an eight-second timeout.
The existing prediction/simulation contracts are typed but no corresponding UI is
built. Those functions use the backend's nonpersistent defaults.

Autocomplete begins at two trimmed characters and debounces for 300 ms. Query
changes/unmount abort the previous request; aborted responses cannot replace newer
results. Loading, no-results and error states are explicit. Arrow keys select
options, Enter navigates, Escape dismisses and leaving the search closes the menu.
Results link via internal `id`, never the provider's `external_id`. Initials replace
unavailable photos. Full profile implementation is deferred.

Model values and rankings always come from the API; production data is never
substituted with test fixtures. `formatMoney` renders millions/thousands, zero and
negative values without modifying the source number. `formatDifference` retains
the sign. Native title text on values offers more precise currency formatting.
Money formatting is presentation only, not another valuation policy.

Current real integration results:

- Haaland returns internal ID **582**, Manchester City, ST, latest season 2025/26;
  clicking or pressing Enter opens `/players/582` and its honest profile shell.
- V1 snapshot shows **€9.68M temporal OOF MAE**, **0.525 R²**, **2,594 observations**
  and five seasons. These are not final all-data model test scores.
- Latest positive preview starts with Igor Thiago: **€94.3M model**, **€65M observed**,
  **+€29.3M difference**. Negative preview starts with William Saliba: **€29.6M model**,
  **€100M observed**, **−€70.4M difference**.
- Ranking text states these are analytical differences on stored training observations,
  not objective transfer valuations.

## Accessibility and responsive behavior

Semantic sections, visible focus rings, a skip link, explicit input label, ARIA
combobox/listbox state, live search announcements and an expanded mobile-menu state
are provided. Signed values and directional text supplement color. Motion respects
`prefers-reduced-motion`. The layout is bounded on ultrawide displays; the pitch is
removed on small screens, rankings stack and mobile navigation collapses. Desktop
and phone browser checks verify no horizontal overflow. Full assistive-technology
auditing and more browser engines remain future validation work.

## Validation

```powershell
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
# Start frontend and real API before the live integration tests:
npx playwright install chromium
npm run test:e2e
```

Vitest/Testing Library tests mock only network/navigation boundaries and cover
debouncing, result rendering, keyboard navigation, internal-ID links, empty/error
states, currency formats, API shapes/errors, metric scope and ranking disclaimers.
Playwright tests use the real local API on desktop and a phone viewport, navigate
all shells, inspect CORS-dependent search and reject browser console/page errors.
Screenshots are stored outside source in ignored `.local/`. Browser binaries are
test tooling, not production assets. Python validation still uses the existing
TEST_DATABASE_URL fixture. Backend/ML files are hashed before and after this session.

Final results: 19 frontend unit tests and two live desktop/mobile browser tests
passed, including the production-built app. Lint, TypeScript and production build
passed; the existing 216 Python tests passed. All 136 protected backend/ML/data
files remained unchanged. Browser tests recorded no console errors or horizontal
overflow. Desktop and mobile screenshots were visually inspected.

## Dependencies and limitations

Existing Next.js 16.3.8 / React 19.3.0 / TypeScript 5.9.3 were retained. Added Tailwind
and its PostCSS plugin, self-hosted Inter/Barlow Condensed fonts; development-only
ESLint/Next config, Vitest, Testing Library/jest-dom, jsdom and Playwright. The npm
lockfile captures the resolved versions. Prettier was used as a one-off formatter.

`npm audit` reports five high-severity entries in a **single development lint-tool
dependency chain**, from eslint-config-next through fast-glob/micromatch to braces
(GHSA-vfj7-8cjw-p6xm). The available braces version remains affected; npm suggests a
major Next ESLint downgrade, which was not applied. This is not five independent
production runtime vulnerabilities. Recheck upstream fixes before CI hardening.

Route shells deliberately contain no profile, simulator, charts or full rankings
features. Next.js request-time model/ranking fetches are not cached; this suits the
current small dataset. TypeScript interfaces are maintained against the API contract,
not generated runtime validators. The local end-to-end test expects the supplied
seeded dataset (including Haaland ID 582). No deployment was performed.

## Files created or changed

- `app/`: layout, homepage, global styles, icon and player/models/rankings shells.
- `components/layout/`: Navbar, Footer.
- `components/home/`: Hero, ModelSnapshot, RankingsPreview, HowItWorks.
- `components/search/PlayerSearch.tsx`, `components/player/PlayerAvatar.tsx`.
- `components/ui/`: States, RouteShell.
- `lib/api/`: types and client; `lib/format.ts`.
- `tests/`: setup, API client, money, search, homepage and fallback tests.
- `e2e/home.spec.ts`, Vitest and Playwright configuration.
- `frontend/.env.example`, PostCSS, ESLint and Next configuration, package manifest/lockfile.
- Root README, `.gitignore`, and this setup document.

The temporary local environment and screenshots are ignored. This document records
Session 12; the player route has since been completed in
[Session 13](PLAYER_PROFILE.md).
