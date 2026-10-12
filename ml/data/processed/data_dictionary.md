# Transfermarkt V1 player-season dataset

Generated from the existing local Transfermarkt CSVs. One row per exact Transfermarkt `player_id` and Premier League `season`. This is the real V1 schema; the generic Session 2 schema remains available in code for future providers.

Empty CSV cells mean missing, never invented zeros. Source zero counts are preserved. IDs are strings and must be read as strings to preserve their original representation.

| Column | Type / unit | Definition |
| --- | --- | --- |
| `player_id` | string | Shared Transfermarkt ID, unchanged; not a name match or model feature. |
| `player_name` | string | Last appearance-context display name in this season; player metadata name only as a missing-name fallback. Display metadata, not a model feature. |
| `season` | YYYY/YY | Derived from verified starting-year `games.season`; join/split metadata. |
| `club` | string | Primary club's name from the last relevant game context in this exact season. |
| `club_id` | string | Historical primary club from `appearances.player_club_id`, never current-club fields. |
| `clubs_in_season` | integer | Number of distinct EPL clubs represented by this player's appearances. |
| `date_of_birth` | ISO date | Player metadata birth date; blank if invalid or historical age falls outside 1–100. |
| `age` | integer, years | Completed years at `season_end_date`, with birthday adjustment. Never present-day age. |
| `position_raw` | string | Original broad `players.position`; undated snapshot, not proven historical. |
| `sub_position_raw` | string | Original detailed `players.sub_position`; undated snapshot, not proven historical. |
| `position` | category or missing | Conservative detailed-label mapping below. Descriptive metadata; exclude from temporal model features until its historical validity is established. |
| `appearances` | integer | Distinct EPL games with an appearance record for the player in this season. |
| `minutes` | integer, minutes | Sum of `minutes_played` from this season's EPL appearances across all clubs. |
| `goals` | integer | Sum of recorded goals from those same appearances. |
| `assists` | integer | Sum of recorded assists from those same appearances. |
| `yellow_cards` | integer | Sum of recorded yellow-card counts; provider semantics retained. |
| `red_cards` | integer | Sum of recorded red-card counts; provider semantics retained. |
| `goals_per_90` | number | `goals / minutes * 90`; missing when minutes are zero. |
| `assists_per_90` | number | `assists / minutes * 90`; missing when minutes are zero. |
| `goal_contributions_per_90` | number | `(goals + assists) / minutes * 90`; missing when minutes are zero. |
| `season_end_date` | ISO date | Actual last EPL game date in the complete season's `games.csv` records. |
| `market_value_eur` | number, EUR | Target only: actual historical valuation nearest season end inside the configured inclusive window. Never an input feature. |
| `market_value_date` | ISO date | Selected historical valuation date. Target audit metadata, never an input feature. |
| `market_value_days_from_season_end` | signed integer, days | Valuation date minus season end. Accepted V1 range 0 through +45. Target audit metadata, never an input feature. |

## Position mapping

| Source sub-position | V1 category |
| --- | --- |
| Goalkeeper | GK |
| Centre-Back | CB |
| Left-Back, Right-Back | FB |
| Defensive Midfield | DM |
| Central Midfield | CM |
| Attacking Midfield | AM |
| Left Winger, Right Winger | W |
| Centre-Forward | ST |
| Left Midfield, Right Midfield, Second Striker, missing or unknown | Missing; original labels preserved |

Broad `Goalkeeper` can map to GK if the detailed label is absent. Other broad categories are not guessed. All three position columns originate in an undated player snapshot; they cannot yet be claimed as season-specific features.

## Multi-club seasons

Aggregate every valid EPL appearance in the same season once. Choose the primary club by total minutes, then appearance count, then lexicographically smallest club ID on an exact tie. Do not discard the other club's statistics. `clubs_in_season` marks this situation; the cleaning report retains primary-club details and each club's minutes/appearances.

## Timing and missingness

The V1 target is the earliest observed valuation on or after the actual season end, no more than 45 days later (both boundaries inclusive). Pre-end valuations are always rejected. No valid target means the player-season is excluded and reported. Conflicting amounts on the same player/date in the window quarantine that player-season. Values are never interpolated.

V1 uses the completed Premier League season to estimate value immediately afterward: `season_end_date <= market_value_date <= season_end_date + 45 days`. No appearance statistics are truncated. No following-season appearances, current-club attributes, transfer records, or valuation amounts enter performance features.

Missing/invalid birth dates yield missing age and birth date; no rows are dropped solely for that. Invalid or conflicting appearance records quarantine the affected player-season rather than producing partial totals. Exact duplicates are removed. Unknown detailed positions remain missing. No statistical imputation is performed.

## Unsupported or deferred fields

V1 intentionally omits starts, shots, shots on target, key passes, passes, pass accuracy, dribbles, tackles, interceptions, and their per-90 variants. Starts require additional validated lineup data; the other performance fields are absent from the six inspected sources. Game-level standings exist but are not promoted to a final-season `club_league_position` without validating their semantics. No zero-filled placeholders are emitted.

See [the integration report](../../../docs/TRANSFERMARKT_DATA.md) for actual counts, coverage, limitations, and commands. See `cleaning_report.json` beside the dataset for file hashes, source columns, ingestion timestamp, configuration, exclusions, and missing-value counts.
