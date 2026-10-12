"""Small synthetic provider fixtures only; never load the real raw exports."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from ml.data_pipeline.providers.transfermarkt import (
    SOURCE_COLUMNS,
    Config,
    build_frames,
    historical_age,
    parse_dates,
    run,
    select_targets,
    write_result,
)


@pytest.fixture
def provider_frames() -> dict[str, pd.DataFrame]:
    data = {
        "competitions": [
            {
                "competition_id": "TEST_EPL",
                "competition_code": "premier-league",
                "country_name": "England",
                "type": "domestic_league",
                "sub_type": "first_tier",
                "total_clubs": "2",
                "url": "https://example.invalid",
            }
        ],
        "games": [
            {
                "game_id": "g1",
                "competition_id": "TEST_EPL",
                "season": "2021",
                "date": "2022-05-01",
                "home_club_id": "10",
                "away_club_id": "20",
                "home_club_goals": "1",
                "away_club_goals": "0",
                "home_club_name": "Historical A",
                "away_club_name": "Historical B",
            },
            {
                "game_id": "g2",
                "competition_id": "TEST_EPL",
                "season": "2021",
                "date": "2022-05-22",
                "home_club_id": "20",
                "away_club_id": "10",
                "home_club_goals": "0",
                "away_club_goals": "2",
                "home_club_name": "Historical B",
                "away_club_name": "Historical A",
            },
        ],
        "appearances": [
            {
                "game_id": "g1",
                "player_id": "001",
                "player_club_id": "10",
                "date": "2022-05-01",
                "player_name": "Test Person",
                "competition_id": "TEST_EPL",
                "minutes_played": "90",
                "goals": "1",
                "assists": "1",
                "yellow_cards": "0",
                "red_cards": "0",
            },
            {
                "game_id": "g2",
                "player_id": "001",
                "player_club_id": "10",
                "date": "2022-05-22",
                "player_name": "Test Person",
                "competition_id": "TEST_EPL",
                "minutes_played": "45",
                "goals": "2",
                "assists": "0",
                "yellow_cards": "1",
                "red_cards": "0",
            },
        ],
        "players": [
            {
                "player_id": "001",
                "name": "Later Display Name",
                "date_of_birth": "2000-06-01 00:00:00",
                "position": "Midfield",
                "sub_position": "Central Midfield",
            }
        ],
        "clubs": [{"club_id": "10"}, {"club_id": "20"}],
        "player_valuations": [
            {"player_id": "001", "date": "2022-06-01", "market_value_in_eur": "1000"}
        ],
    }
    return {name: pd.DataFrame(rows) for name, rows in data.items()}


@pytest.fixture
def provider_config() -> Config:
    return Config(seasons=("2021/22",))


def test_aggregation_and_report(provider_frames: dict, provider_config: Config) -> None:
    result = build_frames(provider_frames, provider_config)
    row = result.rows.iloc[0]
    assert row["player_id"] == "001"
    assert row["player_name"] == "Test Person"
    assert row["minutes"] == 135
    assert row["appearances"] == 2
    assert row["goals"] == 3
    assert row["assists"] == 1
    assert row["yellow_cards"] == 1
    assert row["goals_per_90"] == 2
    assert row["goal_contributions_per_90"] == pytest.approx(4 / 135 * 90)
    assert row["age"] == 21
    assert row["position_raw"] == "Midfield"
    assert row["sub_position_raw"] == "Central Midfield"
    assert row["position"] == "CM"
    assert row["club"] == "Historical A"
    assert row["market_value_days_from_season_end"] == 10
    assert "starts" not in result.rows and "shots" not in result.rows
    assert result.report["competition_id"] == "TEST_EPL"
    assert result.report["appearance_rows_used"] == 2
    assert result.report["player_seasons_before_target_matching"] == 1
    assert result.report["final_rows"] == 1
    assert result.report["rows_excluded"] == 0


def test_other_leagues_and_future_seasons_do_not_leak(
    provider_frames: dict, provider_config: Config
) -> None:
    baseline = build_frames(provider_frames, provider_config).rows
    other_game = provider_frames["games"].iloc[0].to_dict() | {
        "game_id": "foreign",
        "competition_id": "OTHER",
    }
    future_game = other_game | {
        "game_id": "future",
        "competition_id": "TEST_EPL",
        "season": "2022",
        "date": "2023-05-01",
    }
    provider_frames["games"] = pd.concat(
        [provider_frames["games"], pd.DataFrame([other_game, future_game])], ignore_index=True
    )
    original = provider_frames["appearances"].iloc[0].to_dict()
    additions = [
        original | {"game_id": "foreign", "competition_id": "OTHER", "goals": "1000"},
        original | {"game_id": "future", "date": "2023-05-01", "goals": "2000"},
    ]
    provider_frames["appearances"] = pd.concat(
        [provider_frames["appearances"], pd.DataFrame(additions)], ignore_index=True
    )
    pd.testing.assert_frame_equal(build_frames(provider_frames, provider_config).rows, baseline)


def test_selected_future_season_is_aggregated_separately(provider_frames: dict) -> None:
    future_games = provider_frames["games"].copy()
    future_games["game_id"] = ["g3", "g4"]
    future_games["season"] = "2022"
    future_games["date"] = ["2023-05-01", "2023-05-28"]
    future_apps = provider_frames["appearances"].copy()
    future_apps["game_id"] = ["g3", "g4"]
    future_apps["date"] = future_games["date"]
    future_apps["goals"] = "50"
    provider_frames["games"] = pd.concat(
        [provider_frames["games"], future_games], ignore_index=True
    )
    provider_frames["appearances"] = pd.concat(
        [provider_frames["appearances"], future_apps], ignore_index=True
    )
    provider_frames["player_valuations"] = pd.concat(
        [
            provider_frames["player_valuations"],
            pd.DataFrame(
                [{"player_id": "001", "date": "2023-06-01", "market_value_in_eur": "2000"}]
            ),
        ],
        ignore_index=True,
    )
    result = build_frames(provider_frames, Config(seasons=("2021/22", "2022/23")))
    assert result.rows["goals"].tolist() == [3, 100]
    assert result.rows["market_value_eur"].tolist() == [1000, 2000]


def test_historical_birthday_and_missing_age() -> None:
    births = parse_dates(
        pd.Series(
            ["2000-05-23", "2000-05-22", "2000-05-21", "", "invalid", "2030-01-01", "1800-01-01"]
        )
    )
    refs = pd.to_datetime(pd.Series(["2022-05-22"] * len(births)))
    ages = historical_age(births, refs)
    assert ages.iloc[:3].tolist() == [21, 22, 22]
    assert ages.iloc[3:].isna().all()


@pytest.mark.parametrize(
    "offset,accepted",
    [(-30, False), (-1, False), (0, True), (1, True), (45, True), (46, False)],
)
def test_window_boundaries(offset: int, accepted: bool) -> None:
    end = pd.Timestamp("2022-05-22")
    seasons = pd.DataFrame([{"player_id": "001", "season": "2021/22", "season_end_date": end}])
    values = pd.DataFrame(
        [
            {
                "player_id": "001",
                "date": (end + pd.Timedelta(days=offset)).strftime("%Y-%m-%d"),
                "market_value_in_eur": "1000",
            }
        ]
    )
    result, _ = select_targets(seasons, values, Config())
    assert len(result) == int(accepted)


def test_pre_end_target_rejected_even_when_closer() -> None:
    seasons = pd.DataFrame(
        [{"player_id": "001", "season": "2021/22", "season_end_date": pd.Timestamp("2022-05-22")}]
    )
    values = pd.DataFrame(
        [
            {"player_id": "001", "date": "2022-05-21", "market_value_in_eur": "1000"},
            {"player_id": "001", "date": "2022-06-01", "market_value_in_eur": "2000"},
            {"player_id": "001", "date": "2022-06-10", "market_value_in_eur": "3000"},
            {"player_id": "002", "date": "2022-05-22", "market_value_in_eur": "999999"},
        ]
    )
    result, _ = select_targets(seasons, values, Config())
    assert result.iloc[0]["market_value_eur"] == 2000
    assert result.iloc[0]["market_value_days_from_season_end"] == 10


@pytest.mark.parametrize("settings", [{"days_before": 30}, {"days_after": 46}])
def test_v1_configuration_cannot_reintroduce_unsafe_window(settings: dict) -> None:
    with pytest.raises(ValueError, match="V1 requires"):
        Config(**settings)


def test_pre_end_only_target_excludes_row_without_truncating_features(
    provider_frames: dict, provider_config: Config
) -> None:
    original = build_frames(provider_frames, provider_config)
    provider_frames["player_valuations"].loc[0, "date"] = "2022-05-21"
    excluded = build_frames(provider_frames, provider_config)
    assert excluded.rows.empty
    assert excluded.report["rows_without_valid_market_valuation"] == 1
    assert excluded.report["appearance_rows_used"] == original.report["appearance_rows_used"] == 2
    assert excluded.report["player_seasons_before_target_matching"] == 1


def test_shared_ids_not_names(provider_frames: dict, provider_config: Config) -> None:
    provider_frames["players"]["name"] = "Unrelated Name"
    assert len(build_frames(provider_frames, provider_config).rows) == 1
    provider_frames["player_valuations"]["player_id"] = "different_id"
    result = build_frames(provider_frames, provider_config)
    assert result.rows.empty
    assert result.report["rows_without_valid_market_valuation"] == 1
    assert result.report["rows_excluded"] == 1


def test_multiclub_minutes_then_appearances(provider_frames: dict, provider_config: Config) -> None:
    provider_frames["appearances"].loc[1, "player_club_id"] = "20"
    result = build_frames(provider_frames, provider_config)
    assert result.rows.iloc[0]["club_id"] == "10"
    assert result.rows.iloc[0]["clubs_in_season"] == 2
    assert result.rows.iloc[0]["goals"] == 3
    assert result.report["multi_club_player_seasons_final"] == 1
    provider_frames["appearances"].loc[1, "minutes_played"] = "100"
    assert build_frames(provider_frames, provider_config).rows.iloc[0]["club_id"] == "20"
    provider_frames["appearances"].loc[1, "minutes_played"] = "90"
    assert build_frames(provider_frames, provider_config).rows.iloc[0]["club_id"] == "10"


def test_zero_minutes_and_ambiguous_position(
    provider_frames: dict, provider_config: Config
) -> None:
    provider_frames["appearances"]["minutes_played"] = "0"
    provider_frames["players"]["sub_position"] = "Second Striker"
    result = build_frames(provider_frames, provider_config)
    assert (
        result.rows[["goals_per_90", "assists_per_90", "goal_contributions_per_90"]]
        .isna()
        .all()
        .all()
    )
    assert result.rows["position"].isna().all()
    assert result.rows.iloc[0]["sub_position_raw"] == "Second Striker"


def test_unavailable_season_reported(provider_frames: dict) -> None:
    result = build_frames(provider_frames, Config(seasons=("2021/22", "2025/26")))
    assert result.report["seasons"]["2025/26"]["status"] == "excluded_incomplete"
    assert result.report["per_season_final_counts"]["2025/26"] == 0


def test_incomplete_season_cannot_use_last_available_game_as_end(
    provider_frames: dict, provider_config: Config
) -> None:
    provider_frames["games"] = provider_frames["games"].iloc[:1]
    with pytest.raises(ValueError, match="No complete seasons"):
        build_frames(provider_frames, provider_config)


def test_duplicate_appearances_not_double_counted(
    provider_frames: dict, provider_config: Config
) -> None:
    provider_frames["appearances"] = pd.concat(
        [provider_frames["appearances"], provider_frames["appearances"].iloc[:1]], ignore_index=True
    )
    result = build_frames(provider_frames, provider_config)
    assert result.rows.iloc[0]["appearances"] == 2
    assert result.report["duplicate_appearance_rows_removed"] == 1


def test_invalid_or_conflicting_target_rejected(
    provider_frames: dict, provider_config: Config
) -> None:
    other = provider_frames["player_valuations"].copy()
    other["market_value_in_eur"] = "2000"
    provider_frames["player_valuations"] = pd.concat(
        [provider_frames["player_valuations"], other], ignore_index=True
    )
    result = build_frames(provider_frames, provider_config)
    assert result.rows.empty
    assert result.report["valuation_quality"]["conflicting_valuation_player_seasons"] == 1


def test_local_runner_provenance_and_cli(
    tmp_path: Path, provider_frames: dict, provider_config: Config
) -> None:
    for name, frame in provider_frames.items():
        frame.to_csv(tmp_path / f"{name}.csv", index=False)
    result = run(tmp_path, Config(seasons=provider_config.seasons, chunk_size=1))
    assert result.report["raw_rows_read"]["appearances.csv"] == 2
    assert len(result.report["provenance"]["sources"]) == 6
    assert all(len(source["sha256"]) == 64 for source in result.report["provenance"]["sources"])
    output = tmp_path / "output"
    command = [
        sys.executable,
        "-m",
        "scripts.build_training_dataset",
        "--provider",
        "transfermarkt",
        "--raw-dir",
        str(tmp_path),
        "--seasons",
        "2021/22",
        "--output",
        str(output),
    ]
    process = subprocess.run(
        command, cwd=Path(__file__).resolve().parents[2], text=True, capture_output=True
    )
    assert process.returncode == 0, process.stderr
    report = json.loads((output / "cleaning_report.json").read_text())
    assert report["final_rows"] == 1
    assert (output / "player_seasons.csv").exists()
    with pytest.raises(FileExistsError):
        write_result(result, output)
    assert set(SOURCE_COLUMNS) == set(provider_frames)
