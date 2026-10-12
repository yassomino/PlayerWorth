# Data Pipeline

Session 2 implementation and usage are documented in [DATA_PIPELINE.md](DATA_PIPELINE.md).
The [data dictionary](../ml/data/processed/data_dictionary.md) defines the output template.
Session 2.5 now produces the real Transfermarkt V1 dataset from the existing local CSVs.
See [TRANSFERMARKT_DATA.md](TRANSFERMARKT_DATA.md) for the verified schemas, source coverage,
valuation policy, limitations, and reproduction command. The Session 3 baseline is documented
in [LINEAR_REGRESSION.md](LINEAR_REGRESSION.md); the source pipeline is unchanged.

## Goal

Create the clean historical dataset used to train PlayerWorth.

Target:

```text
market_value_eur
```

Each row should represent one player for one clearly defined season or observation period.

## Initial Scope

Start with:

- English Premier League
- multiple historical seasons
- player performance statistics
- historical market values

Do not expand globally until the Premier League pipeline works.

## Desired Columns

```text
player_id
player_name
season
club
age
position
appearances
starts
minutes
goals
assists
shots
shots_on_target
key_passes
passes
pass_accuracy
dribbles
tackles
interceptions
yellow_cards
red_cards
club_league_position
market_value_eur
market_value_date
```

Derived features may include:

```text
goals_per_90
assists_per_90
goal_contributions_per_90
shots_per_90
key_passes_per_90
tackles_per_90
interceptions_per_90
```

## Data Source Rules

Document for every source:

- source name
- URL
- fields used
- retrieval date
- license / usage restrictions if known
- static dataset vs API

Prefer legitimate datasets/APIs. Avoid brittle scraping unless explicitly approved.

## Player Identity Matching

Do not blindly join on names.

Preferred order:

1. shared external player ID
2. maintained mapping table
3. normalized name + club + season
4. normalized name + DOB
5. fuzzy matching only as reviewed fallback

## Cleaning

Handle:

- duplicates
- missing values
- impossible ages
- inconsistent positions
- inconsistent clubs
- currencies
- zero-minute players
- transferred players
- duplicate player-season rows

Produce a cleaning report.

Example:

```text
Rows loaded: 4523
Duplicates removed: 31
Missing market value: 214
Final rows: 4092
```

## Position Standardization

Suggested categories:

```text
GK
CB
FB
DM
CM
AM
W
ST
```

Document the mapping.

## Market Value Timing

Avoid leakage.

Example rule:

```text
Use the nearest known market value within 60 days after season end.
```

The exact rule may change, but it must be explicit and consistent.

Never use future-season information to predict an earlier valuation.

## Outputs

```text
ml/data/raw/
ml/data/processed/player_seasons.csv
ml/data/processed/data_dictionary.md
ml/data/processed/cleaning_report.json
```

## Suggested Scripts

```text
scripts/
├── ingest_players.py
├── normalize_players.py
├── merge_sources.py
└── build_training_dataset.py
```

## Acceptance Criteria

- clean Premier League historical dataset exists
- every modeling row has a target
- data dictionary exists
- merge process is reproducible
- leakage risk has been reviewed
- identity mapping is repeatable
- value timing is documented

## First Codex Prompt

```text
Read README.md and docs/DATA_README.md.

Implement only the initial data-pipeline structure:
1. raw ingestion interfaces
2. normalization utilities
3. merge utilities
4. final dataset builder

Do not invent data and do not build the ML model yet.

Add TODOs where external datasets are still required.
Add unit tests for normalization functions.
```
