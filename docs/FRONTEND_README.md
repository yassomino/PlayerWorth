# Frontend

## V1 implementation status

The four product routes are implemented: home/search, player profile and unsaved
simulator, Model Lab, and rankings. Session 15 establishes the permanent midnight
navy, aqua and violet identity with original PW geometry and self-hosted Inter /
Barlow Condensed. The implemented components use semantic CSS and Recharts;
shadcn/ui in the original plan below is not an installed dependency. No player or
club imagery is bundled.

See [brand and design](BRAND_AND_DESIGN.md), [release validation](RELEASE_VALIDATION.md)
and [deployment](DEPLOYMENT.md) for the current system and hosting status. The
remaining sections preserve the original product direction, not a list of newly
authorized features.

## Goal

Build a polished football analytics product, not a generic AI dashboard.

Stack:

- Next.js
- TypeScript
- App Router
- Tailwind CSS
- shadcn/ui
- Recharts

## Design Direction

Inspiration:

- Football Manager depth
- Transfermarkt familiarity
- modern sports-broadcast graphics
- restrained financial-terminal analytics

Avoid:

- generic SaaS landing-page look
- excessive gradients
- giant "AI" branding
- fake data in production UI
- arbitrary confidence gauges

Prefer:

- dark neutral background
- club/player photography where licensed/available
- bold typography
- strong stat hierarchy
- dense but readable analytics
- responsive mobile layout

## Pages

### `/`

Homepage.

Sections:

1. Hero
2. Player search
3. Featured / trending players
4. Undervalued players
5. Model overview
6. CTA to Model Lab

Hero copy concept:

```text
How much is a footballer really worth?

Explore model-estimated player values built from performance data.
```

### `/players/[id]`

Most important page.

Show:

- player name
- club
- badge
- position
- age
- nationality
- season
- predicted value
- observed market value
- difference
- core stats
- per-90 stats
- charts
- model used

### `/players/[id]/simulator`

Or embed simulator on player page.

Controls could include:

- age
- goals
- assists
- minutes
- shots
- key passes
- tackles

As sliders change, call prediction API with debouncing.

Show:

```text
Original predicted value
Updated predicted value
Difference
```

Always label this as a hypothetical model simulation.

### `/models`

Model Lab.

Show cards for:

- Linear Regression
- Ridge
- Random Forest
- XGBoost

Metrics:

- MAE
- RMSE
- R²

Charts:

- actual vs predicted
- coefficient / importance chart when valid

### `/rankings`

Tabs:

- Undervalued
- Overvalued

Each row:

- player
- club
- observed value
- predicted value
- model difference

## Component Ideas

```text
components/
├── player/
│   ├── PlayerCard.tsx
│   ├── PlayerHeader.tsx
│   ├── PlayerStats.tsx
│   └── PlayerValueCard.tsx
├── simulator/
│   ├── SimulatorSlider.tsx
│   └── ValueDelta.tsx
├── model/
│   ├── ModelCard.tsx
│   ├── MetricCard.tsx
│   └── ActualPredictedChart.tsx
├── rankings/
│   └── RankingsTable.tsx
└── search/
    └── PlayerSearch.tsx
```

## API Layer

Do not scatter `fetch()` calls everywhere.

Create:

```text
frontend/lib/api/
```

Typed functions:

```ts
searchPlayers()
getPlayer()
predictPlayerValue()
getModels()
getRankings()
```

Define TypeScript API types.

## Loading / Errors

Every data surface needs:

- loading state
- empty state
- error state

Use skeletons for player pages.

## Accessibility

- semantic HTML
- keyboard-search support
- visible focus states
- chart summaries/text where possible
- sufficient contrast

## Responsive Design

Must work well at:

- phone
- tablet
- desktop
- ultrawide

Do not design desktop-only.

## Acceptance Criteria

- homepage looks intentional and football-specific
- player search works
- player page uses live backend data
- Transfer Simulator calls real prediction API
- Model Lab shows real metrics
- rankings show real backend values
- responsive behavior is solid
- no hardcoded fake production statistics

## First Codex Prompt

```text
Read README.md and docs/FRONTEND_README.md.

Implement only the frontend foundation:
1. Next.js App Router project
2. Tailwind
3. shadcn/ui setup
4. global design tokens
5. app shell/navigation
6. homepage shell
7. typed API client
8. reusable loading/error components

Do not hardcode fake players.
Do not build the full simulator yet.
The visual direction should feel like a premium football analytics product, not generic SaaS.
```
