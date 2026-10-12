# Data Pipeline

Session 2 implemented the generic data-layer architecture described below. Session 2.5 adds
a provider adapter for the user-supplied Transfermarkt exports and generates the real V1
dataset and cleaning report. See [TRANSFERMARKT_DATA.md](TRANSFERMARKT_DATA.md) for its
verified source contract, run command, results, and limitations. The data pipeline itself
does not train models; Session 3 is documented separately in [LINEAR_REGRESSION.md](LINEAR_REGRESSION.md).

The provider path uses Pandas, exact shared IDs, match-based season aggregation, and the
corrected V1 valuation window from season end through 45 days afterward, inclusive.
The generic path below retains its original post-statistics-cutoff policy and schema.

## Data flow

```text
Local canonical CSV exports + source manifests
    -> ingest_players: validate provenance, preserve IDs, hash source bytes
    -> normalize_players: validate records, apply reviewed aliases, report rejects
    -> merge_sources: resolve identities, apply explicit date policies, add per-90 fields
    -> build_training_dataset: validate and write player_seasons.csv + cleaning_report.json
```

The four scripts are thin wrappers around `ml/data_pipeline`. The generic path uses only
Python's standard library; the Transfermarkt adapter uses pinned Pandas/NumPy dependencies.
`ml/preprocessing/`, training, inference, API, database, and frontend functionality are unchanged.

Intermediate JSON files retain provenance and normalization reports. The merge artifact includes accepted rows and the complete cleaning report, so it can be inspected even when no rows qualify. The build stage refuses empty datasets and existing output files. Choose a new run directory to rerun; no overwrite flag is provided.

## Input contracts

Source-specific adapters must eventually translate selected datasets into these canonical CSV columns. Preserve the original exports separately. Do not rename units without converting them or replace historical attributes with present-day values.

Generic statistics require `player_id`, `player_name`, `season`, `club`, `competition`,
`statistics_as_of`, and `minutes`. The generic schema permits richer optional statistics
listed in `DATA_README.md`; missing values stay missing. The current [data dictionary](../ml/data/processed/data_dictionary.md)
describes the narrower real Transfermarkt V1 output. `competition` must explicitly be `EPL`
or `English Premier League`. The generic league-position guard accepts 1–20; older seasons
with a different league size require a reviewed extension before ingestion.

Valuations require `player_id`, `market_value_eur`, `currency=EUR`, and `market_value_date`. Optional `player_name`, `club`, `season`, and `date_of_birth` enable exact fallback matching. Blank optional values are allowed. Source IDs must remain strings, including leading zeros.

The manifest supplies `id_namespace` to every row. Both CSVs may supply it too, but it must agree with the manifest. Equal ID strings from different providers are **not** shared IDs. Sources without stable IDs need an explicitly reviewed identity adapter before use.

Both kinds may provide `date_of_birth` as an ISO date. For statistics, `statistics_as_of` is the latest date represented in **any** supplied feature, including league position and age; it is not the export/download date. Every season uses its own policy.

No currency or localized-number guessing occurs: amounts are plain numeric EUR, counts are nonnegative integers, minutes may be fractional, and pass accuracy is a 0–100 percentage. Empty cells become missing values; strings such as `N/A`, currency symbols, or millions suffixes require an explicit source adapter. Nonfinite and negative numeric values are rejected.

## Source manifest template

Create one manifest alongside each local CSV, under `ml/data/raw/`. This is a template only; replace every TODO and supply actual column names. It is deliberately not a runnable source configuration.

```json
{
  "source_name": "TODO: provider and dataset/version",
  "url": "TODO: original source URL",
  "kind": "TODO: statistics or valuations",
  "source_type": "TODO: static_csv or api_export",
  "retrieval_date": "TODO: YYYY-MM-DD",
  "license": "TODO: license or explicitly document unknown status",
  "usage_restrictions": "TODO: permitted use and restrictions",
  "id_namespace": "TODO: stable provider ID namespace",
  "fields_used": []
}
```

`fields_used` lists canonical input columns actually present in the CSV. Additional manifest fields may record the original-export hash, adapter version, original-to-canonical field mapping, and provider-specific provenance. All manifest fields and the canonical CSV SHA-256 are carried into the final report. A manifest records provenance; it does not establish legal permission by itself.

## Identity matching and review

The ordered matching rules are:

1. Exact `(id_namespace, player_id)` shared by both sources.
2. Explicit crosswalk from a statistics identity to a valuation identity.
3. Exact normalized name + normalized club + season.
4. Exact normalized name + date of birth.

There is no fuzzy matching. A human-reviewed fuzzy candidate can later become a crosswalk entry. Names are Unicode-normalized, case-folded, and whitespace-normalized; accents and punctuation are retained. Club variants require supplied aliases. Positions accept `GK`, `CB`, `FB`, `DM`, `CM`, `AM`, `W`, and `ST`, with source-specific aliases supplied explicitly. Broad categories such as `DF` are not guessed.

The crosswalk is a CSV with this header:

```text
statistics_namespace,statistics_player_id,valuation_namespace,valuation_player_id
```

Conflicting crosswalk targets fail validation. Missing explicit targets do not fall through to weaker matches. Shared IDs that contradict a mapping, conflicting known birth dates, conflicting same-namespace IDs, and ambiguous fallback matches are reported. Distinct statistics IDs cannot silently resolve to the same valuation player within one season.

Exact normalized duplicates are removed and counted. Conflicting records for the same statistics player-season, including multiple club stints, are excluded for review. No arbitrary club is chosen and transfer rows are not automatically summed. A future source adapter must distinguish season totals from stints and define how club/context fields are assigned without double-counting.

## Valuation-date policy

There is no default valuation window, season calendar, or assumed 60-day rule. The merge stage requires a nonempty `policies` mapping with a policy for every statistics season. This configuration template is intentionally incomplete:

```json
{
  "club_aliases": {},
  "position_aliases": {},
  "policies": {
    "TODO: YYYY/YY": {
      "statistics_cutoff": "TODO: YYYY-MM-DD",
      "window_start": "TODO: YYYY-MM-DD",
      "window_end": "TODO: YYYY-MM-DD",
      "next_season_start": "TODO: YYYY-MM-DD",
      "selection": "TODO: earliest or latest"
    }
  }
}
```

At merge time the pipeline enforces:

```text
statistics_as_of <= statistics_cutoff <= window_start <= window_end < next_season_start
```

Window boundaries are inclusive. Only observations inside the approved window can become targets. The configuration explicitly selects the earliest or latest observation; conflicting amounts for the same identity/date inside that window cause rejection. Out-of-window valuations cannot be substituted when the window is empty. The same identity can have many valuation observations without creating a many-to-many dataset join.

These are structural checks, not proof that provider metadata is historically accurate. TODO: select real sources, verify their date semantics and historical availability, define each season's boundaries and observation timing, and review leakage before a modeling dataset is accepted. In particular, a recent retrieval date does not make a current attribute valid for an earlier season.

Club aliases must map directly to stable canonical names, without chains. Position aliases cannot redefine canonical position codes. Use the same aliases during normalization and merge; a changed alias configuration requires renormalizing the original inputs.

## Commands after real inputs are selected

Run from the repository root. The file names below are expected future local inputs, not bundled data. `pipeline.json` contains the reviewed aliases and policies. Intermediate files live in an ignored directory under `ml/data/raw/`.

```powershell
python -m scripts.ingest_players --csv ml/data/raw/statistics.csv --manifest ml/data/raw/statistics.manifest.json --output ml/data/raw/run/statistics.ingested.json
python -m scripts.ingest_players --csv ml/data/raw/valuations.csv --manifest ml/data/raw/valuations.manifest.json --output ml/data/raw/run/valuations.ingested.json
python -m scripts.normalize_players --input ml/data/raw/run/statistics.ingested.json --config ml/data/raw/pipeline.json --output ml/data/raw/run/statistics.normalized.json
python -m scripts.normalize_players --input ml/data/raw/run/valuations.ingested.json --config ml/data/raw/pipeline.json --output ml/data/raw/run/valuations.normalized.json
python -m scripts.merge_sources --statistics ml/data/raw/run/statistics.normalized.json --valuations ml/data/raw/run/valuations.normalized.json --config ml/data/raw/pipeline.json --output ml/data/raw/run/merged.json
python -m scripts.build_training_dataset --input ml/data/raw/run/merged.json --output ml/data/processed
```

Add `--mapping <reviewed-crosswalk.csv>` to the merge command when needed. `merge_sources` can also consume ingested envelopes directly; it always runs normalization and validation. Use module invocation (`python -m scripts...`), which resolves imports from the repository root.

The report records original input counts, duplicate counts, rejected statistics counts, missing output fields, zero-minute rows, rejection reasons, matching methods, selected valuation dates/identities, policies, reviewed mappings, aliases, source manifests, source hashes, and the merged-artifact hash. Upstream normalization details remain included. Inspect both rejected rows and accepted fallback matches before accepting real data. Invalid source rows are excluded explicitly; source completeness must be reviewed before fallback matching is trusted.

## Tests and generic-provider extension work

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Tests cover normalization, exact matching precedence, ambiguity, namespace collisions, mapping conflicts, date boundaries, missing values, duplicates, transfer conflicts, per-90 behavior, multi-season output, ingestion, and the complete CLI flow using temporary synthetic fixtures.

For additional providers, the generic workflow still requires the following source decisions.
The Transfermarkt-specific choices and remaining limitations are documented separately:

- Obtain licensed historical EPL statistics and historical valuation observations for multiple seasons.
- Implement and document source-specific field/unit adapters, stable IDs, and historical snapshot semantics.
- Review club/position aliases and player crosswalks; decide how transfers and duplicate provider rows are represented.
- Define actual season cutoffs, target windows, and valuation selection, with a leakage review.
- Document source-dependent age reference dates, pass-accuracy definitions, and coverage/missingness decisions.
- Run the pipeline on real inputs and review its cleaning report and fallback matches.

Session 3 has not begun. No training models or evaluation metrics are created by this pipeline.
