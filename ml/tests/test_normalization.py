import pytest

from ml.data_pipeline.normalization import (
    normalize_club,
    normalize_name,
    normalize_position,
    normalize_record,
    normalize_season,
)


def test_names_preserve_accents_and_do_not_guess() -> None:
    assert normalize_name("  TEST\tPlayer  ") == "test player"
    assert normalize_name("Jose\u0301") == normalize_name("José")
    assert normalize_name("José") != normalize_name("Jose")
    assert normalize_name(None) == ""


def test_clubs_require_explicit_aliases() -> None:
    assert normalize_club(" TEST FC ") == "test fc"
    assert normalize_club("TEST FC", {"Test FC": "Test Football Club"}) == "test football club"
    assert normalize_club("Test FC") != normalize_club("Test Football Club")


def test_aliases_cannot_change_after_repeated_normalization() -> None:
    with pytest.raises(ValueError, match="stable canonical"):
        normalize_club("a", {"a": "b", "b": "c"})
    with pytest.raises(ValueError, match="empty"):
        normalize_club("a", {"a": ""})
    with pytest.raises(ValueError, match="redefine"):
        normalize_position("CM", {"CM": "DM"})


@pytest.mark.parametrize("raw", ["2022/23", "2022-2023", "2022/2023"])
def test_season_formats(raw: str) -> None:
    assert normalize_season(raw) == "2022/23"


@pytest.mark.parametrize("raw", ["2022", "22/23", "2022/24", "2022/1923"])
def test_bad_seasons(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_season(raw)


def test_positions_are_reviewed() -> None:
    assert normalize_position(" cm ") == "CM"
    assert normalize_position("wide", {"wide": "W"}) == "W"
    assert normalize_position("") is None
    with pytest.raises(ValueError):
        normalize_position("DF")


def test_normalization_preserves_ids_and_missing_counts(stats_row: dict) -> None:
    result = normalize_record(stats_row, "statistics")
    assert result["player_id"] == "001"
    assert result["player_name"] == "Test Player"
    assert result["goals"] == 2
    assert result["tackles"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("minutes", "-1"),
        ("minutes", "nan"),
        ("minutes", "inf"),
        ("minutes", ""),
        ("goals", "1.5"),
        ("goals", True),
        ("age", "101"),
        ("age", "0"),
        ("club_league_position", "21"),
        ("pass_accuracy", "101"),
        ("starts", "13"),
        ("shots_on_target", "11"),
        ("statistics_as_of", "2023-02-30"),
        ("competition", "Other League"),
        ("player_id", ""),
        ("id_namespace", ""),
    ],
)
def test_invalid_statistics_rejected(stats_row: dict, field: str, value: object) -> None:
    with pytest.raises(ValueError):
        normalize_record(dict(stats_row, **{field: value}), "statistics")


@pytest.mark.parametrize(
    "field,value",
    [
        ("currency", "GBP"),
        ("currency", ""),
        ("market_value_eur", "€1m"),
        ("market_value_eur", "nan"),
        ("market_value_eur", ""),
        ("market_value_eur", "-2"),
        ("market_value_date", "20230601"),
    ],
)
def test_invalid_valuations_rejected(value_row: dict, field: str, value: str) -> None:
    with pytest.raises(ValueError):
        normalize_record(dict(value_row, **{field: value}), "valuations")
