# Session 2.5 — Transfermarkt V1 integration

The adapter reads the user-supplied CSVs already present in `ml/data/raw/`. It downloads nothing,
uses no API, and leaves all raw files unchanged. Session 3 now consumes this unchanged dataset;
see [LINEAR_REGRESSION.md](LINEAR_REGRESSION.md) for the separate baseline results.

## Reproduce

From the repository root, using Python 3.11 or newer:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.build_training_dataset --provider transfermarkt --raw-dir ml/data/raw --output ml/data/processed
```

The default seasons are 2021/22 through 2025/26. Override with `--seasons 2021/22 2022/23`; `--days-before` accepts only 0; `--days-after` may narrow the default 45-day maximum. Existing outputs are never overwritten: use a fresh output directory for comparison runs. The generic `--input` build path remains supported.

Provider code: `ml/data_pipeline/providers/transfermarkt.py`. The existing build script dispatches it through `ml/data_pipeline/cli.py`. Reusable per-90 helpers and streamed file hashing are shared with the generic pipeline; generic identity matching and valuation policies remain unchanged. Pandas/NumPy are pinned in the project metadata and full-test requirements.

## Verified source schemas

League discovery requires the unique competition with country `England`, code `premier-league`, type `domestic_league`, and subtype `first_tier`. The actual identifier is **GB1**. Seasons use the starting year: `2021`, `2022`, `2023`, `2024`, `2025`. These values were inspected before coding.

Only the following six files are read. The complete original header and selected columns are also preserved in the cleaning report.

### competitions.csv — 65 raw rows

**Available:** `competition_id`, `competition_code`, `name`, `sub_type`, `type`, `country_id`, `country_name`, `domestic_league_code`, `confederation`, `total_clubs`, `url`.

**Read:** `competition_id`, `competition_code`, `country_name`, `type`, `sub_type`, `total_clubs`, `url`.

### games.csv — 88,958 raw rows

**Available:** `game_id`, `competition_id`, `season`, `round`, `date`, `home_club_id`, `away_club_id`, `home_club_goals`, `away_club_goals`, `home_club_position`, `away_club_position`, `home_club_manager_name`, `away_club_manager_name`, `stadium`, `attendance`, `referee`, `url`, `home_club_formation`, `away_club_formation`, `home_club_name`, `away_club_name`, `aggregate`, `competition_type`.

**Read:** `game_id`, `competition_id`, `season`, `date`, `home_club_id`, `away_club_id`, `home_club_goals`, `away_club_goals`, `home_club_name`, `away_club_name`.

### players.csv — 50,149 raw rows

**Available:** `player_id`, `first_name`, `last_name`, `name`, `last_season`, `current_club_id`, `player_code`, `country_of_birth`, `city_of_birth`, `country_of_citizenship`, `date_of_birth`, `sub_position`, `position`, `foot`, `height_in_cm`, `contract_expiration_date`, `agent_name`, `image_url`, `international_caps`, `international_goals`, `current_national_team_id`, `url`, `current_club_domestic_competition_id`, `current_club_name`, `market_value_in_eur`, `highest_market_value_in_eur`.

**Read:** `player_id`, `name`, `date_of_birth`, `position`, `sub_position`.

### clubs.csv — 796 raw rows

**Available:** `club_id`, `club_code`, `name`, `domestic_competition_id`, `total_market_value`, `squad_size`, `average_age`, `foreigners_number`, `foreigners_percentage`, `national_team_players`, `stadium_name`, `stadium_seats`, `net_transfer_record`, `coach_name`, `last_season`, `filename`, `url`.

**Read:** `club_id`.

### appearances.csv — 1,894,350 raw rows

**Available:** `appearance_id`, `game_id`, `player_id`, `player_club_id`, `player_current_club_id`, `date`, `player_name`, `competition_id`, `yellow_cards`, `red_cards`, `goals`, `assists`, `minutes_played`.

**Read:** `game_id`, `player_id`, `player_club_id`, `date`, `player_name`, `competition_id`, `yellow_cards`, `red_cards`, `goals`, `assists`, `minutes_played`.

### player_valuations.csv — 656,301 raw rows

**Available:** `player_id`, `date`, `market_value_in_eur`, `current_club_name`, `current_club_id`, `player_club_domestic_competition_id`.

**Read:** `player_id`, `date`, `market_value_in_eur`.

`game_events.csv`, `game_lineups.csv`, `club_games.csv`, `transfers.csv`, `countries.csv`, and `national_teams.csv` are not loaded. Starts cannot be reliably derived from appearances alone, so lineup processing is intentionally deferred. Club metadata contributes only an ID consistency check; historical club names come from games.

Appearance CSV chunks contain at most 100,000 rows by default. Game-ID filtering retains only relevant appearances before concatenation; joins and aggregations are vectorized. The adapter never iterates over all raw appearance rows in Python. Per-90 helpers run only on the much smaller aggregated player-season table.

## Actual season coverage and output

| Season | Raw season | Games | Last EPL game | Appearance rows | Before targets | Excluded targets | Final rows |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| 2021/22 | 2021 | 380 | 2022-05-22 | 10,369 | 508 | 17 | 491 |
| 2022/23 | 2022 | 380 | 2023-05-28 | 11,345 | 554 | 32 | 522 |
| 2023/24 | 2023 | 380 | 2024-05-19 | 11,384 | 570 | 36 | 534 |
| 2024/25 | 2024 | 380 | 2025-05-25 | 11,567 | 562 | 19 | 543 |
| 2025/26 | 2025 | 380 | 2026-05-24 | 11,492 | 537 | 33 | 504 |

All five requested seasons have 20 clubs, 380 scored games, a complete directed home/away pairing set, and appearance coverage for every game. An incomplete season is excluded rather than treating its last available match as the true season end. These checks establish structural coverage, not independent verification of every football statistic.

The run uses **56,157** appearances to create **2,731** player-seasons. **137** lack an acceptable target and are excluded. Final output: **2,594 rows, 1,139 unique players**. No invalid or duplicate relevant appearances were found; no player-season was excluded before target matching. No invalid, duplicate, or conflicting valuation records were found in this export.

## Aggregation and historical metadata

Join appearances to games by exact `game_id`, then use only the requested league and season. Validate appearance competition/date and historical club membership against the game. Count distinct game IDs and sum actual minutes, goals, assists, and cards. Exact duplicates are removed; conflicting/invalid appearance records quarantine the entire affected player-season to avoid partial totals. No following-season appearances enter an earlier row.

Age is completed years between date of birth and the actual final game date, with birthday adjustment. Missing, unparsable, future, or implausible birth dates produce missing age/date of birth. The current output has none missing.

There are **60 multi-club player-seasons**, all retained. Sum statistics across every EPL club in the season. Select the primary club by minutes, then appearances, then lexicographically smallest club ID on ties. Game-context names label that historical club. The report records each primary club, number of clubs, and per-club minutes/appearances. Current-club fields and transfers are not read.

Player `position` has broad values Attack, Defender, Midfield, Goalkeeper, and Missing across the raw export. The more detailed `sub_position` permits conservative mapping. Left Midfield, Right Midfield, and Second Striker remain unmapped rather than guessed. Both original fields are retained.

**Historical-position limitation:** player metadata has no effective-date history. Raw and mapped positions are descriptive snapshot metadata, not approved temporal model inputs. They must be excluded from temporal model features until historical validity is established. Player display names are metadata too.

## Target alignment and leakage limits

Use the exact shared Transfermarkt `player_id`; no name or fuzzy matching. Select the observed valuation with the smallest absolute distance from actual season end on or after season end and within **45 days after**, inclusive. This selects the earliest valid post-season observation. Conflicting amounts on the same player/date inside the window exclude that player-season. No out-of-window fallback is allowed.

Actual selected offsets: **+2 to +40 days**; median absolute distance **10 days**. There are **0 before**, **0 on**, and **2,594 after** season end.

The target amount, valuation date, and signed date offset are target/audit columns, never predictor features. Features use only matches from the exact season. Current player market values, highest market values, current club data, and future transfers are not read.

**Temporal correction:** V1 enforces `season_end_date <= market_value_date <= season_end_date + 45 days`. The previous rule admitted 24 pre-end targets. None had an eligible post-season replacement, so all 24 were removed. Completed-season statistics are unchanged. The cleaning report records the removed identities and comparison with the prior dataset.

**Valuation coverage limitation:** the export ends on **2026-06-12**, while the 2025/26 window extends to **2026-07-08**. Its match season is structurally complete, but its full possible target window is not covered. The report flags this explicitly; later observations are not fabricated. The 33 missing targets in that season may partly reflect this limitation.

## Missingness and position categories

Only mapped `position` is missing: **26 rows**. All other 23 output columns have zero missing cells in this run. The full per-column counts are in the report. Zero-minute rates would remain missing; no accepted player-season has zero minutes in this export.

| Category | Rows |
| --- | ---: |
| CB | 495 |
| FB | 427 |
| W | 387 |
| ST | 324 |
| CM | 326 |
| DM | 228 |
| GK | 200 |
| AM | 181 |
| <unmapped> | 26 |

V1 omits starts, shots, shots on target, key passes, passes, pass accuracy, dribbles, tackles, interceptions, and corresponding richer per-90 statistics. These metrics are not present in the six inputs or cannot be reliably derived. Game-level league positions are available but not adopted as a season-level feature until their semantics are validated. See the [V1 data dictionary](../ml/data/processed/data_dictionary.md) for all 24 actual output columns.

## Provenance, Git safety, and validation

`cleaning_report.json` records each source filename, all available/read columns, row count, SHA-256, UTC ingestion timestamp, Python/Pandas/NumPy versions, adapter hash, output hash, league selection, season filters, valuation window, exclusions, missingness, multi-club contributions, and quality issues. The dataset archive URL, original retrieval time, and license were not supplied and remain explicitly unknown. The competition URL read from the dataset is not represented as the archive URL.

Existing `.gitignore` rules exclude `/ml/data/raw/*` and re-include `.gitkeep`. The twelve downloaded CSVs remain untouched and are not committed. Generated CSV/report files remain ignored; the Markdown dictionary is allowed in Git.

Validation commands:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

The test suite uses synthetic, temporary fixtures only. It covers league/season isolation, future-season leakage, aggregation, historical age, exact IDs, nearest targets, inclusive window edges, pre-end rejection, multi-club handling, zero-minute rates, missing targets, incomplete seasons, duplicate records, and provenance/CLI execution. Real-data validation additionally compares repeat-run CSV bytes and audits aggregates and valuation choices against the local source CSVs.

Remaining limitations: undated positions; truncated 2025/26 valuation window;
absent richer statistics and starts; missing target selection bias; provider accuracy and
card/assist semantics; unknown archive/license metadata. This integration stage does not train models.
