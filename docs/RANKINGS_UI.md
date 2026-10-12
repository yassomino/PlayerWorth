# Session 14 — Full rankings

`/rankings` compares model estimates with stored observed market values. It is a
read-only analytical view, not a declaration of objective player value.

## API and semantics

Only existing endpoints are used through the shared typed client:

| UI direction | GET endpoint | Backend order |
| --- | --- | --- |
| Model Above Observed | `/api/v1/rankings/undervalued` | Largest positive difference first |
| Model Below Observed | `/api/v1/rankings/overvalued` | Most negative difference first |

Every request includes `limit=20` and the selected season. Only the selected list
is fetched, not both directions or all seasons. Rank, ID, player name, club,
position, observed value, estimate and difference come directly from the API.
The frontend does not sort, calculate predictions, create ranking records or write
to the database. GET requests do not persist predictions. No persistence control
or parameter is added.

```text
difference_eur = predicted_value_eur - observed_value_eur
```

The reused `ValueDelta` component shows a signed EUR amount and explicit above/below
text. Colors are supplementary. Full amounts are available through value titles;
compact amounts reuse the existing formatter. Missing club/position remains
unavailable/unmapped, never invented. Club means primary club for the stored season.

## Selection, URLs and recovery

The five selector options are the verified V1 cohort, newest first: 2025/26 through
2021/22. Default is 2025/26, the latest stored season in this cohort. The existing
API has no season-discovery endpoint. Update `lib/rankings.ts` deliberately if the
cohort expands; unavailable selected seasons receive a recovery message.

Example deep link:

```text
/rankings?season=2024%2F25&direction=below
```

The server parses initial query values. Client state and native browser history
keep controls, requests, refresh and Back/Forward consistent. Direction buttons
are keyboard-accessible toggles with `aria-pressed`; the season select is labeled.
Duplicate/invalid query parameters show an invalid-selection state and do not
silently load another ranking. A recovery button opens latest above-observed data.

Each selection remounts the result request. Cleanup cancels the previous request,
and late responses cannot replace the chosen list. Skeleton rows appear while
loading. Navigation, controls and disclaimer remain available during loading/errors.
Empty API lists have an explicit empty state. 404/422 responses advise choosing
another season; service/model/network errors use a safe localized retry message.
No backend internals are displayed. Retry requests the same selected list.

Player links use the internal ID returned by the API and carry the row's season:
`/players/{id}?season=...`. No fixed player IDs are used for navigation. The result
summary shows API model identity/version, season, returned count and eligible/
excluded counts. Eligibility counts cover both directions before sign filtering;
they are not pagination totals. The page intentionally caps at 20 rows with no
infinite scrolling or invented total count.

## Interpretation and layout

The prominent disclaimer states that these are analytical model outputs, not
objective valuations. Final V1 was fitted on all five stored seasons: rankings
describe known observations and are not unseen-season evaluation. A Model Lab
link explains that distinction. Negative outputs are displayed as returned; no
clipping or "correction" occurs in the UI.

Desktop uses a complete table. On phones the same records become readable cards
with player/club, rank, position, separately labeled observed/model values and
signed difference text. No mobile-only fabricated fields are added. Layout stays
inside the page width. Styles are scoped in `components/ui/analytics.css`, with
global and semantic color tokens; future palette redesign is independent of data
and interactions. No photos, proprietary assets or new dependency were introduced.

## Real local validation, 6 October 2026

For `playerworth_v1` v1.0.0 and 2025/26, 504 rows are eligible and zero are excluded
by the rankings endpoint. These counts are after the earlier data-pipeline exclusions.

| Direction leader | Observed EUR | Model estimate EUR | Difference EUR |
| --- | ---: | ---: | ---: |
| Igor Thiago · above observed | 65,000,000 | 94,286,296 | +29,286,296 |
| William Saliba · below observed | 100,000,000 | 29,618,136 | -70,381,864 |

The live test compares names, order, values and links with fresh API responses,
rather than requiring these specific leaders or internal IDs forever. It toggles
direction, selects 2024/25, refreshes, goes Back, then opens the returned player's
profile with the right season. Both desktop and mobile variants pass.

Validation totals: **57 frontend tests**, **10 live browser tests**, **216 Python
tests**, plus lint, TypeScript and production build all passed. Successful browser
flows have no console/page errors. Screenshots were inspected; checks at 320, 390,
768, 1280 and 1440 pixels found no page-level overflow. Model Lab and existing
homepage/Haaland profile/simulator checks also pass. Protected hashes for 136
backend/ML/data/evaluation files are unchanged.

See [MODEL_LAB.md](MODEL_LAB.md) for commands and the complete Session 14 file inventory.
The live services remain local; there was no deployment or Session 15 work.

## Remaining limitations

- Season options are the known V1 cohort, not automatic discovery of future imports.
- Up to 20 sign-matching rows are shown per request; this is not an exhaustive export.
- Rankings inherit missing-target selection, snapshot position and model limitations.
- No authentication, favorites, comparison tools, prediction-history UI or live data.
- Browser validation covers Chromium desktop and mobile emulation only.
