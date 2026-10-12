# PlayerWorth brand and design

PlayerWorth V1 uses an original football analytics identity: **The game. Another
value.** A compact PW mark, condensed matchday headlines, a drawn pitch and restrained
data cards connect football with model interpretation. No league crest, club logo,
player photograph or copied Premier League/FPL asset is used.

## Design tokens

The single palette lives in `frontend/app/globals.css`. Page styles use semantic
variables; `--accent` and `--surface` are compatibility aliases, not separate palettes.

| Role | Token | Value |
|---|---|---|
| Canvas | `--background` | `#0c1021` |
| Card / raised / emphasis surface | `--surface-1/2/3` | `#151a31` / `#1d2440` / `#28304e` |
| Primary text / supporting text | `--foreground` / `--muted` | `#f3f5ff` / `#b3bbd4` |
| Primary action / selected state | `--primary` | `#56e2dc` |
| Secondary accent / methodology | `--secondary` | `#b4a0ff` |
| Occasional highlight | `--highlight` | `#ff91b1` |
| Positive / negative difference | `--positive` / `--negative` | `#83e1b5` / `#ffad9b` |
| Decorative / control boundary | `--border` / `--control-border` | `#35405e` / `#697694` |
| Keyboard focus | `--focus` | `#84eff0` |

Chart colors alias the primary, secondary and highlight tokens. Difference colors
always accompany a signed amount and explanatory text; they do not imply investment
advice. The standalone SVG favicon mirrors the palette because it cannot inherit page CSS.

Inter handles body text and tabular data; Barlow Condensed handles headlines and
large values. Both are locally packaged fonts. Supporting labels have an 11px floor;
body copy and controls are larger. Controls use 8–12px radii, major surfaces 18px,
spacing grows in 8px steps, and the content width is bounded on ultrawide screens.

## Page system

- **Home:** search first, an original pitch illustration, live model snapshot,
  ranking previews and a concise explanation of the model's five inputs.
- **Player:** historical identity and season selector, distinct estimate/observation,
  season totals, accessible valuation chart/table, and an unsaved simulator.
- **Model Lab:** current model, exploratory comparisons, temporal folds, pooled
  evidence, feature importance and limitations remain separate sections.
- **Rankings:** persistent season/direction controls, signed differences, readable
  desktop table and mobile cards. No objective “bargain” claims.

Home, Players, Rankings and Model Lab form the main navigation. Players points to
the homepage search; a duplicate player-index page is unnecessary. Mobile navigation
opens below the header, closes on navigation or Escape, and returns keyboard focus
to its toggle on Escape. There is a skip link, visible focus, semantic headings,
explicit chart grouping, error recovery and reduced-motion support.

## QA and screenshots

Automated axe checks cover loaded home, profile, Model Lab, rankings and 404 pages.
The width sweep checks all four product routes at 320, 360, 390, 430, 768, 1024,
1280, 1440, 1920 and 2560px. Tables may scroll within their own labelled region;
the page itself must not overflow. This does not replace a human screen-reader audit.

Curated browser captures are in [screenshots](screenshots/). Debug captures and
test traces remain in ignored local output. See [release validation](RELEASE_VALIDATION.md)
for actual results and browser limitations.
