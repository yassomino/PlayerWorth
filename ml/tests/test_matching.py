import pytest

from ml.data_pipeline.matching import PlayerMatcher, ValuationPolicy, select_valuation
from ml.data_pipeline.normalization import normalize_record


def test_shared_id_precedes_names(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(
        dict(
            value_row,
            id_namespace="test_stats",
            player_id="001",
            player_name="Different Display Name",
        ),
        "valuations",
    )
    assert PlayerMatcher([value]).match(player).method == "shared_id"


def test_mapping_precedes_fallback(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    first = normalize_record(value_row, "valuations")
    other = dict(first, player_id="V2")
    matcher = PlayerMatcher([first, other], {("test_stats", "001"): ("test_values", "V2")})
    assert matcher.match(player).records[0]["player_id"] == "V2"
    assert matcher.match(player).method == "mapping"


def test_missing_mapping_target_does_not_fallback(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(value_row, "valuations")
    match = PlayerMatcher([value], {("test_stats", "001"): ("test_values", "absent")}).match(player)
    assert match.issue == "mapped_id_missing"


def test_fallback_order(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(value_row, "valuations")
    assert PlayerMatcher([value]).match(player).method == "name_club_season"
    assert PlayerMatcher([dict(value, club="other")]).match(player).method == "name_date_of_birth"


def test_name_alone_never_matches(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(dict(value_row, club="", date_of_birth=""), "valuations")
    assert PlayerMatcher([value]).match(player).issue == "unmatched_identity"


def test_ambiguous_names_do_not_use_weaker_fallback(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(value_row, "valuations")
    other = dict(value, player_id="V2", date_of_birth="1999-01-01")
    assert PlayerMatcher([value, other]).match(player).issue == "ambiguous_identity"


def test_conflicting_ids_and_birthdates(stats_row: dict, value_row: dict) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(value_row, "valuations")
    assert (
        PlayerMatcher([dict(value, id_namespace="test_stats")]).match(player).issue
        == "conflicting_id"
    )
    assert (
        PlayerMatcher([dict(value, date_of_birth="1999-01-01")]).match(player).issue
        == "conflicting_date_of_birth"
    )


def test_multiple_dates_not_multiple_players(
    stats_row: dict, value_row: dict, policies: dict
) -> None:
    player = normalize_record(stats_row, "statistics")
    value = normalize_record(value_row, "valuations")
    later = dict(value, market_value_date="2023-06-30", market_value_eur=2000)
    future = dict(value, market_value_date="2024-06-01", market_value_eur=999999)
    match = PlayerMatcher([value, later, future]).match(player)
    assert match.method == "name_club_season"
    selected, issue = select_valuation(match.records, policies["2022/23"])
    assert issue is None
    assert selected["market_value_eur"] == 2000


def test_date_boundaries_and_conflicts(value_row: dict, policies: dict) -> None:
    value = normalize_record(value_row, "valuations")
    policy = policies["2022/23"]
    assert (
        select_valuation((dict(value, market_value_date="2023-05-31"),), policy)[1]
        == "no_valuation_in_window"
    )
    assert (
        select_valuation((dict(value, market_value_date="2023-07-01"),), policy)[1]
        == "no_valuation_in_window"
    )
    assert (
        select_valuation((value, dict(value, market_value_eur=2000)), policy)[1]
        == "conflicting_valuations"
    )


def test_earliest_selection(value_row: dict) -> None:
    value = normalize_record(value_row, "valuations")
    policy = ValuationPolicy("2023-05-31", "2023-06-01", "2023-06-30", "2023-08-01", "earliest")
    selected, _ = select_valuation((dict(value, market_value_date="2023-06-30"), value), policy)
    assert selected["market_value_date"] == "2023-06-01"


@pytest.mark.parametrize(
    "changes",
    [
        {"selection": "nearest"},
        {"window_start": "2023-05-01"},
        {"window_end": "2023-08-01"},
        {"next_season_start": "2023-06-15"},
    ],
)
def test_invalid_policy(changes: dict) -> None:
    params = dict(
        statistics_cutoff="2023-05-31",
        window_start="2023-06-01",
        window_end="2023-06-30",
        next_season_start="2023-08-01",
        selection="latest",
    )
    with pytest.raises(ValueError):
        ValuationPolicy(**(params | changes))
