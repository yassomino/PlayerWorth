"""Historical EPL aggregation from local Transfermarkt CSV exports only."""

import csv
import hashlib
import json
import platform
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..features import per_90
from ..ingestion import hash_file
from ..normalization import normalize_season

DEFAULT_SEASONS = tuple(f"{year}/{str(year + 1)[-2:]}" for year in range(2021, 2026))
POSITION_MAP = {
    "Goalkeeper": "GK",
    "Centre-Back": "CB",
    "Left-Back": "FB",
    "Right-Back": "FB",
    "Defensive Midfield": "DM",
    "Central Midfield": "CM",
    "Attacking Midfield": "AM",
    "Left Winger": "W",
    "Right Winger": "W",
    "Centre-Forward": "ST",
}
STAT_COLUMNS = ["minutes", "goals", "assists", "yellow_cards", "red_cards"]
OUTPUT_COLUMNS = [
    "player_id",
    "player_name",
    "season",
    "club",
    "club_id",
    "clubs_in_season",
    "date_of_birth",
    "age",
    "position_raw",
    "sub_position_raw",
    "position",
    "appearances",
    *STAT_COLUMNS,
    "goals_per_90",
    "assists_per_90",
    "goal_contributions_per_90",
    "season_end_date",
    "market_value_eur",
    "market_value_date",
    "market_value_days_from_season_end",
]
SOURCE_COLUMNS = {
    "competitions": [
        "competition_id",
        "competition_code",
        "country_name",
        "type",
        "sub_type",
        "total_clubs",
        "url",
    ],
    "games": [
        "game_id",
        "competition_id",
        "season",
        "date",
        "home_club_id",
        "away_club_id",
        "home_club_goals",
        "away_club_goals",
        "home_club_name",
        "away_club_name",
    ],
    "appearances": [
        "game_id",
        "player_id",
        "player_club_id",
        "date",
        "player_name",
        "competition_id",
        "yellow_cards",
        "red_cards",
        "goals",
        "assists",
        "minutes_played",
    ],
    "players": ["player_id", "name", "date_of_birth", "position", "sub_position"],
    "clubs": ["club_id"],
    "player_valuations": ["player_id", "date", "market_value_in_eur"],
}


@dataclass(frozen=True)
class Config:
    seasons: tuple[str, ...] = DEFAULT_SEASONS
    days_before: int = 0
    days_after: int = 45
    chunk_size: int = 100_000

    def __post_init__(self) -> None:
        if not self.seasons or len(set(self.seasons)) != len(self.seasons):
            raise ValueError("Provide distinct seasons")
        if any(normalize_season(s) != s for s in self.seasons):
            raise ValueError("Use canonical YYYY/YY seasons")
        if self.days_before != 0 or not 0 <= self.days_after <= 45:
            raise ValueError("V1 requires zero pre-season-end days and at most 45 days after")
        if self.chunk_size < 1:
            raise ValueError("Chunk size must be positive")


@dataclass
class Result:
    rows: pd.DataFrame
    report: dict[str, Any]


def parse_dates(values: pd.Series) -> pd.Series:
    """Accept the observed ISO date and ISO midnight timestamp source formats."""
    valid_shape = values.str.fullmatch(r"\d{4}-\d{2}-\d{2}( 00:00:00)?", na=False)
    return pd.to_datetime(
        values.where(valid_shape).str.slice(0, 10), format="%Y-%m-%d", errors="coerce"
    )


def historical_age(births: pd.Series, reference: pd.Series) -> pd.Series:
    before_birthday = (reference.dt.month < births.dt.month) | (
        (reference.dt.month == births.dt.month) & (reference.dt.day < births.dt.day)
    )
    age = (reference.dt.year - births.dt.year - before_birthday.astype(int)).astype("Int64")
    return age.where(births.notna() & age.between(1, 100))


def resolve_competition(competitions: pd.DataFrame) -> pd.Series:
    selected = competitions.loc[
        competitions["country_name"].eq("England")
        & competitions["competition_code"].eq("premier-league")
        & competitions["type"].eq("domestic_league")
        & competitions["sub_type"].eq("first_tier")
    ]
    if len(selected) != 1:
        raise ValueError("Expected exactly one English Premier League competition record")
    return selected.iloc[0]


def select_targets(
    seasons: pd.DataFrame, valuations: pd.DataFrame, config: Config
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Exact ID join; choose the earliest valuation on/after the completed season."""
    values = valuations.copy()
    values["market_value_date"] = parse_dates(values["date"])
    values["market_value_eur"] = pd.to_numeric(values["market_value_in_eur"], errors="coerce")
    valid = (
        values["market_value_date"].notna()
        & values["player_id"].ne("")
        & values["market_value_eur"].ge(0)
        & np.isfinite(values["market_value_eur"])
    )
    invalid_count = int((~valid).sum())
    values = values.loc[valid, ["player_id", "market_value_date", "market_value_eur"]]
    before = len(values)
    values = values.drop_duplicates()
    duplicates = before - len(values)
    conflicts = (
        values.groupby(["player_id", "market_value_date"])["market_value_eur"]
        .transform("nunique")
        .gt(1)
    )
    values["conflict"] = conflicts
    candidates = seasons[["player_id", "season", "season_end_date"]].merge(
        values, on="player_id", how="inner"
    )
    candidates["market_value_days_from_season_end"] = (
        candidates["market_value_date"] - candidates["season_end_date"]
    ).dt.days
    candidates = candidates.loc[
        candidates["market_value_days_from_season_end"].between(0, config.days_after)
    ].copy()
    conflicted = candidates.loc[candidates["conflict"], ["player_id", "season"]].drop_duplicates()
    if len(conflicted):
        candidates = candidates.merge(
            conflicted.assign(reject=True), on=["player_id", "season"], how="left"
        )
        candidates = candidates.loc[candidates["reject"].isna()]
    candidates["distance"] = candidates["market_value_days_from_season_end"].abs()
    chosen = candidates.sort_values(
        ["distance", "market_value_days_from_season_end"], ascending=[True, False]
    ).drop_duplicates(["player_id", "season"])
    return chosen[
        [
            "player_id",
            "season",
            "market_value_eur",
            "market_value_date",
            "market_value_days_from_season_end",
        ]
    ], {
        "invalid_valuation_rows": invalid_count,
        "duplicate_valuation_rows_removed": duplicates,
        "conflicting_valuation_player_seasons": len(conflicted),
    }


def build_frames(frames: dict[str, pd.DataFrame], config: Config = Config()) -> Result:
    """Vectorized, in-memory adapter core; tests supply only tiny synthetic frames."""
    competition = resolve_competition(frames["competitions"])
    league_id = competition["competition_id"]
    club_count = int(competition["total_clubs"])
    if club_count < 2:
        raise ValueError("Competition total_clubs must be at least two")
    years = {s[:4]: s for s in config.seasons}
    games = (
        frames["games"]
        .loc[
            frames["games"]["competition_id"].eq(league_id) & frames["games"]["season"].isin(years)
        ]
        .copy()
    )
    games = games.drop_duplicates()
    if games["game_id"].duplicated().any() or games["game_id"].eq("").any():
        raise ValueError("Missing or conflicting game IDs in selected seasons")
    games["season"] = games["season"].map(years)
    games["game_date"] = parse_dates(games["date"])
    appearance_source = frames["appearances"]
    appearances = appearance_source.loc[appearance_source["game_id"].isin(games["game_id"])].copy()
    appearances = appearances.rename(
        columns={
            "date": "appearance_date",
            "competition_id": "appearance_competition",
            "minutes_played": "minutes",
        }
    )
    duplicates = int(appearances.duplicated().sum())
    appearances = appearances.drop_duplicates()
    appearances = appearances.merge(
        games.drop(columns="date"), on="game_id", how="inner", validate="many_to_one"
    )
    appearance_rows_selected = len(appearances) + duplicates
    conflicting = appearances.duplicated(["game_id", "player_id"], keep=False)
    invalid = (
        conflicting
        | appearances["player_id"].eq("")
        | appearances["appearance_competition"].ne(league_id)
        | parse_dates(appearances["appearance_date"]).ne(appearances["game_date"])
        | ~(
            appearances["player_club_id"].eq(appearances["home_club_id"])
            | appearances["player_club_id"].eq(appearances["away_club_id"])
        )
    )
    for column in STAT_COLUMNS:
        appearances[column] = pd.to_numeric(appearances[column], errors="coerce")
        invalid |= (
            appearances[column].isna()
            | appearances[column].lt(0)
            | ~np.isfinite(appearances[column])
            | appearances[column].mod(1).ne(0)
        )
    bad_keys = appearances.loc[invalid, ["player_id", "season"]].drop_duplicates()
    all_keys = appearances[["player_id", "season"]].drop_duplicates()
    invalid_appearance_rows = int(invalid.sum())
    # An invalid match record quarantines the whole player-season, avoiding partial totals.
    appearances = appearances.merge(
        bad_keys.assign(bad=True), on=["player_id", "season"], how="left"
    )
    appearances = appearances.loc[appearances["bad"].isna()].copy()
    season_report = {}
    complete = []
    for season in config.seasons:
        group = games.loc[games["season"].eq(season)]
        played = appearances.loc[appearances["season"].eq(season)]
        clubs = set(group["home_club_id"]) | set(group["away_club_id"])
        score_columns = group[["home_club_goals", "away_club_goals"]].apply(
            pd.to_numeric, errors="coerce"
        )
        reasons = []
        if len(group) != club_count * (club_count - 1):
            reasons.append("unexpected_game_count")
        if len(clubs) != club_count or "" in clubs:
            reasons.append("unexpected_club_count")
        if (
            group.duplicated(["home_club_id", "away_club_id"]).any()
            or group["home_club_id"].eq(group["away_club_id"]).any()
        ):
            reasons.append("invalid_round_robin_pairs")
        if (
            group["game_date"].isna().any()
            or score_columns.isna().any().any()
            or score_columns.lt(0).any().any()
        ):
            reasons.append("unplayed_or_invalid_games")
        if played["game_id"].nunique() != len(group):
            reasons.append("missing_appearance_coverage")
        if group.empty:
            reasons.append("season_unavailable")
        end = group["game_date"].max()
        season_report[season] = {
            "games_found": len(group),
            "expected_games": club_count * (club_count - 1),
            "clubs": len(clubs),
            "games_with_appearances": int(played["game_id"].nunique()),
            "season_end_date": None if pd.isna(end) else end.strftime("%Y-%m-%d"),
            "status": "excluded_incomplete" if reasons else "complete",
            "issues": reasons,
        }
        if not reasons:
            complete.append(season)
    appearances = appearances.loc[appearances["season"].isin(complete)].copy()
    if appearances.empty:
        raise ValueError(f"No complete seasons with valid appearances: {season_report}")
    appearances["club"] = appearances["home_club_name"].where(
        appearances["player_club_id"].eq(appearances["home_club_id"]), appearances["away_club_name"]
    )
    keys = ["player_id", "season"]
    seasons = appearances.groupby(keys, as_index=False)[STAT_COLUMNS].sum()
    counts = appearances.groupby(keys).agg(
        appearances=("game_id", "nunique"), clubs_in_season=("player_club_id", "nunique")
    )
    seasons = seasons.merge(counts, on=keys, validate="one_to_one")
    club_totals = appearances.groupby([*keys, "player_club_id"], as_index=False).agg(
        club_minutes=("minutes", "sum"), club_appearances=("game_id", "nunique")
    )
    primary = club_totals.sort_values(
        ["club_minutes", "club_appearances", "player_club_id"], ascending=[False, False, True]
    ).drop_duplicates(keys)
    # Use the last known name in this season's match context for the chosen club.
    club_names = appearances.sort_values(["game_date", "game_id"]).drop_duplicates(
        [*keys, "player_club_id"], keep="last"
    )
    primary = primary.merge(
        club_names[[*keys, "player_club_id", "club"]],
        on=[*keys, "player_club_id"],
        validate="one_to_one",
    )
    seasons = seasons.merge(
        primary[[*keys, "player_club_id", "club"]].rename(columns={"player_club_id": "club_id"}),
        on=keys,
        validate="one_to_one",
    )
    display_names = appearances.sort_values(["game_date", "game_id"]).drop_duplicates(
        keys, keep="last"
    )
    seasons = seasons.merge(display_names[[*keys, "player_name"]], on=keys, validate="one_to_one")
    seasons["season_end_date"] = pd.to_datetime(
        seasons["season"].map({s: d["season_end_date"] for s, d in season_report.items()})
    )
    players = frames["players"].drop_duplicates()
    if players["player_id"].duplicated().any():
        raise ValueError("Conflicting player metadata IDs")
    players = players.rename(
        columns={"position": "position_raw", "sub_position": "sub_position_raw"}
    )
    seasons = seasons.merge(players, on="player_id", how="left", validate="many_to_one")
    seasons["player_name"] = seasons["player_name"].replace("", pd.NA).fillna(seasons["name"])
    seasons["date_of_birth"] = parse_dates(seasons["date_of_birth"])
    seasons["age"] = historical_age(seasons["date_of_birth"], seasons["season_end_date"])
    seasons["date_of_birth"] = seasons["date_of_birth"].where(seasons["age"].notna())
    seasons["position"] = seasons["sub_position_raw"].map(POSITION_MAP)
    seasons.loc[
        seasons["position_raw"].eq("Goalkeeper") & seasons["sub_position_raw"].fillna("").eq(""),
        "position",
    ] = "GK"
    for stat in ("goals", "assists"):
        seasons[f"{stat}_per_90"] = [
            per_90(float(n), float(m))
            for n, m in zip(seasons[stat], seasons["minutes"], strict=True)
        ]
    seasons["goal_contributions_per_90"] = [
        per_90(float(n), float(m))
        for n, m in zip(seasons["goals"] + seasons["assists"], seasons["minutes"], strict=True)
    ]
    targets, valuation_report = select_targets(seasons, frames["player_valuations"], config)
    final = seasons.merge(targets, on=keys, how="inner", validate="one_to_one")
    excluded = seasons.merge(targets[keys].assign(has_target=True), on=keys, how="left")
    excluded = excluded.loc[excluded["has_target"].isna(), keys]
    multi = seasons.loc[
        seasons["clubs_in_season"].gt(1), [*keys, "club_id", "club", "clubs_in_season"]
    ]
    final = final[OUTPUT_COLUMNS].sort_values(["season", "player_id"]).reset_index(drop=True)
    for column in ("date_of_birth", "season_end_date", "market_value_date"):
        final[column] = final[column].dt.strftime("%Y-%m-%d")
    final = final.replace("", pd.NA)
    for season, item in season_report.items():
        item["appearance_rows_used"] = int(appearances["season"].eq(season).sum())
        item["player_seasons_before_target"] = int(seasons["season"].eq(season).sum())
        item["final_rows"] = int(final["season"].eq(season).sum())
        item["without_valid_target"] = item["player_seasons_before_target"] - item["final_rows"]
    offsets = final["market_value_days_from_season_end"]
    valuation_dates = parse_dates(frames["player_valuations"]["date"])
    last_valuation = valuation_dates.max()
    for item in season_report.values():
        item["valuation_window_end"] = (
            (pd.Timestamp(item["season_end_date"]) + pd.Timedelta(days=config.days_after)).strftime(
                "%Y-%m-%d"
            )
            if item["season_end_date"]
            else None
        )
        item["valuation_export_reaches_window_end"] = bool(
            pd.notna(last_valuation)
            and item["valuation_window_end"]
            and last_valuation >= pd.Timestamp(item["valuation_window_end"])
        )
    report = {
        "provider": "Transfermarkt user-supplied local CSV export",
        "competition_id": league_id,
        "competition_url": competition["url"],
        "configuration": asdict(config),
        "season_source_representation": "starting year",
        "seasons": season_report,
        "appearance_rows_selected": appearance_rows_selected,
        "appearance_rows_used": len(appearances),
        "duplicate_appearance_rows_removed": duplicates,
        "invalid_appearance_rows": invalid_appearance_rows,
        "player_seasons_selected": len(all_keys),
        "player_seasons_excluded_before_target": len(all_keys) - len(seasons),
        "player_seasons_before_target_matching": len(seasons),
        "rows_without_valid_market_valuation": len(excluded),
        "rows_excluded": len(all_keys) - len(final),
        "final_rows": len(final),
        "unique_players": int(final["player_id"].nunique()),
        "per_season_final_counts": {s: int(final["season"].eq(s).sum()) for s in config.seasons},
        "missing_values": {c: int(final[c].isna().sum()) for c in OUTPUT_COLUMNS},
        "multi_club_player_seasons_before_target": len(multi),
        "multi_club_player_seasons_final": int(final["clubs_in_season"].gt(1).sum()),
        "multi_club_details": multi.to_dict("records"),
        "multi_club_contributions": club_totals.merge(multi[keys], on=keys).to_dict("records"),
        "multi_club_strategy": (
            "minutes descending, appearances descending, club ID lexical ascending"
        ),
        "position_values_encountered": seasons["position_raw"]
        .fillna("<missing>")
        .value_counts()
        .to_dict(),
        "sub_position_values_encountered": seasons["sub_position_raw"]
        .fillna("<missing>")
        .value_counts()
        .to_dict(),
        "position_categories_final": final["position"]
        .fillna("<unmapped>")
        .value_counts()
        .to_dict(),
        "excluded_without_target": excluded.to_dict("records"),
        "invalid_appearance_player_seasons": bad_keys.to_dict("records"),
        "unknown_club_ids": sorted(set(seasons["club_id"]) - set(frames["clubs"]["club_id"])),
        "valuation_quality": valuation_report,
        "valuation_window_statistics": {
            "days_before": config.days_before,
            "days_after": config.days_after,
            "min_offset": None if final.empty else int(offsets.min()),
            "max_offset": None if final.empty else int(offsets.max()),
            "median_absolute_offset": None if final.empty else float(offsets.abs().median()),
            "before": int(offsets.lt(0).sum()),
            "on": int(offsets.eq(0).sum()),
            "after": int(offsets.gt(0).sum()),
            "source_last_valuation_date": None
            if pd.isna(last_valuation)
            else last_valuation.strftime("%Y-%m-%d"),
        },
        "unresolved_data_quality_issues": [
            "Player position/sub_position metadata is an undated snapshot, not proven historical; "
            "exclude from temporal model features until validated.",
            "Source archive URL, original retrieval timestamp, and license were not supplied; "
            "no claims about them are inferred.",
            "Complete game and appearance coverage does not certify correctness "
            "of every provider statistic.",
        ],
    }
    for season, item in season_report.items():
        if not item["valuation_export_reaches_window_end"]:
            report["unresolved_data_quality_issues"].append(
                f"{season}: valuation export does not cover the full configured post-season window."
            )
        if item["status"] != "complete":
            report["unresolved_data_quality_issues"].append(
                f"{season}: incomplete game/appearance coverage; excluded."
            )
    if final["position"].isna().any():
        report["unresolved_data_quality_issues"].append(
            f"{int(final['position'].isna().sum())} rows retain unmapped positions; "
            "raw labels preserved."
        )
    if final["age"].isna().any():
        report["unresolved_data_quality_issues"].append(
            f"{int(final['age'].isna().sum())} rows have unavailable/invalid birth dates "
            "and missing age."
        )
    return Result(final, report)


def run(raw_dir: Path, config: Config = Config()) -> Result:
    """Read six required sources, filtering large appearance chunks immediately."""
    frames = {}
    provenance = []
    ingestion_time = datetime.now(timezone.utc).isoformat()
    order = ("competitions", "games", "players", "clubs", "appearances", "player_valuations")
    for name in order:
        path = raw_dir / f"{name}.csv"
        with path.open(encoding="utf-8-sig", newline="") as stream:
            header = next(csv.reader(stream))
        if len(header) != len(set(header)) or not set(SOURCE_COLUMNS[name]).issubset(header):
            raise ValueError(f"Unexpected {name} schema: {header}")
        chunks = []
        raw_count = 0
        for chunk in pd.read_csv(
            path,
            usecols=SOURCE_COLUMNS[name],
            dtype=str,
            keep_default_na=False,
            chunksize=config.chunk_size,
        ):
            raw_count += len(chunk)
            if name == "appearances":
                league = resolve_competition(frames["competitions"])["competition_id"]
                games = frames["games"]
                ids = games.loc[
                    games["competition_id"].eq(league)
                    & games["season"].isin([s[:4] for s in config.seasons]),
                    "game_id",
                ]
                chunk = chunk.loc[chunk["game_id"].isin(ids)]
            chunks.append(chunk)
        frames[name] = (
            pd.concat(chunks, ignore_index=True)
            if chunks
            else pd.DataFrame(columns=SOURCE_COLUMNS[name])
        )
        provenance.append(
            {
                "filename": path.name,
                "sha256": hash_file(path),
                "raw_rows": raw_count,
                "columns_available": header,
                "columns_read": SOURCE_COLUMNS[name],
            }
        )
    result = build_frames(frames, config)
    result.report["provenance"] = {
        "source_name": "Transfermarkt CSV dataset supplied by user",
        "source_type": "local_csv",
        "dataset_archive_url": None,
        "original_retrieval_date": None,
        "license": "not supplied",
        "ingestion_timestamp_utc": ingestion_time,
        "sources": provenance,
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__,
        "numpy_version": np.__version__,
        "adapter_sha256": hash_file(Path(__file__)),
    }
    result.report["raw_rows_read"] = {p["filename"]: p["raw_rows"] for p in provenance}
    return result


def write_result(result: Result, output_dir: Path) -> None:
    if result.rows.empty:
        raise ValueError("No accepted player-seasons; no production CSV written")
    if result.rows.duplicated(["player_id", "season"]).any():
        raise ValueError("Duplicate output player-season identity")
    dataset_path, report_path = (
        output_dir / "player_seasons.csv",
        output_dir / "cleaning_report.json",
    )
    if dataset_path.exists() or report_path.exists():
        raise FileExistsError("Outputs already exist; choose a new output directory")
    csv_text = result.rows.to_csv(index=False, lineterminator="\n")
    result.report["output_sha256"] = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
    report_text = json.dumps(result.report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    output_dir.mkdir(parents=True, exist_ok=True)
    with dataset_path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(csv_text)
    with report_path.open("x", encoding="utf-8", newline="") as stream:
        stream.write(report_text)
