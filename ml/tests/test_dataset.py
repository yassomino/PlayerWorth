import csv
import json
from pathlib import Path

import pytest

from ml.data_pipeline.dataset import OUTPUT_COLUMNS, build_dataset, write_dataset
from ml.data_pipeline.matching import ValuationPolicy


def test_build_deduplicates_and_preserves_missing(
    stats_row: dict, value_row: dict, policies: dict
) -> None:
    result = build_dataset([stats_row, stats_row], [value_row, value_row], policies=policies)
    assert len(result.rows) == 1
    assert set(result.rows[0]) == set(OUTPUT_COLUMNS)
    assert result.rows[0]["player_id"] == "test_stats:001"
    assert result.rows[0]["goal_contributions_per_90"] == 0.5
    assert result.rows[0]["tackles_per_90"] is None
    assert result.report["duplicates_removed"] == {"statistics": 1, "valuations": 1}


def test_transferred_player_not_silently_aggregated(
    stats_row: dict, value_row: dict, policies: dict
) -> None:
    result = build_dataset(
        [stats_row, dict(stats_row, club="Second Test Club")], [value_row], policies=policies
    )
    assert result.rows == []
    assert result.report["issues"][0]["reason"] == "conflicting_player_season"
    assert result.report["issues"][0]["rejected_rows"] == 2


def test_many_stats_ids_cannot_share_one_valuation(
    stats_row: dict, value_row: dict, policies: dict
) -> None:
    result = build_dataset(
        [stats_row, dict(stats_row, player_id="002")], [value_row], policies=policies
    )
    assert result.rows == []
    assert {issue["reason"] for issue in result.report["issues"]} == {"many_to_one_identity"}


def test_missing_target_excluded(stats_row: dict, value_row: dict, policies: dict) -> None:
    result = build_dataset([stats_row], [dict(value_row, market_value_eur="")], policies=policies)
    assert not result.rows
    assert {issue["reason"] for issue in result.report["issues"]} == {
        "invalid_row",
        "unmatched_identity",
    }


def test_statistics_cannot_cross_cutoff(stats_row: dict, value_row: dict, policies: dict) -> None:
    result = build_dataset(
        [dict(stats_row, statistics_as_of="2023-06-01")], [value_row], policies=policies
    )
    assert not result.rows
    assert result.report["issues"][0]["reason"] == "statistics_after_cutoff"


def test_policy_required_for_every_season(stats_row: dict, value_row: dict, policies: dict) -> None:
    with pytest.raises(ValueError, match="explicit policies"):
        build_dataset([stats_row], [value_row], policies={})
    with pytest.raises(ValueError, match="Missing valuation policies"):
        build_dataset([dict(stats_row, season="2021/22")], [value_row], policies=policies)


def test_multiple_seasons_and_repeatable_output(
    stats_row: dict, value_row: dict, policies: dict
) -> None:
    policies = dict(
        policies,
        **{
            "2023/24": ValuationPolicy(
                "2024-05-31", "2024-06-01", "2024-06-30", "2024-08-01", "latest"
            )
        },
    )
    statistics = [
        stats_row,
        dict(stats_row, season="2023/24", statistics_as_of="2024-05-31", goals="4"),
    ]
    values = [
        value_row,
        dict(value_row, season="2023/24", market_value_date="2024-06-01", market_value_eur="2000"),
    ]
    first = build_dataset(statistics, values, policies=policies)
    second = build_dataset(list(reversed(statistics)), list(reversed(values)), policies=policies)
    assert first.rows == second.rows
    assert [row["market_value_eur"] for row in first.rows] == [1000, 2000]


def test_write_dataset_and_report(
    tmp_path: Path, stats_row: dict, value_row: dict, policies: dict
) -> None:
    result = build_dataset([stats_row], [value_row], policies=policies)
    write_dataset(result, tmp_path)
    with (tmp_path / "player_seasons.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["tackles"] == ""
    assert json.loads((tmp_path / "cleaning_report.json").read_text())["final_rows"] == 1
    with pytest.raises(FileExistsError):
        write_dataset(result, tmp_path)


def test_empty_result_does_not_write_production_csv(tmp_path: Path, policies: dict) -> None:
    with pytest.raises(ValueError, match="No accepted rows"):
        write_dataset(build_dataset([], [], policies=policies), tmp_path)
    assert not list(tmp_path.iterdir())


def test_modified_features_rejected(
    tmp_path: Path, stats_row: dict, value_row: dict, policies: dict
) -> None:
    result = build_dataset([stats_row], [value_row], policies=policies)
    result.rows[0]["goals_per_90"] = 999
    with pytest.raises(ValueError, match="per-90"):
        write_dataset(result, tmp_path)
    assert not list(tmp_path.iterdir())
