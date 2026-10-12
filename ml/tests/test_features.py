import pytest

from ml.data_pipeline.features import DERIVED_COLUMNS, add_per_90, per_90


def test_per_90() -> None:
    assert per_90(10, 900) == 1
    assert per_90(0, 900) == 0


@pytest.mark.parametrize("stat,minutes", [(2, 0), (None, 90), (2, None), (None, None)])
def test_missing_denominator_or_stat(stat: float | None, minutes: float | None) -> None:
    assert per_90(stat, minutes) is None


@pytest.mark.parametrize(
    "stat,minutes", [(-1, 90), (1, -90), (float("nan"), 90), (1, float("inf"))]
)
def test_invalid_numbers(stat: float, minutes: float) -> None:
    with pytest.raises(ValueError):
        per_90(stat, minutes)


def test_all_features_and_input_unchanged() -> None:
    row = {
        "minutes": 180,
        "goals": 2,
        "assists": 4,
        "shots": 6,
        "key_passes": 8,
        "tackles": 10,
        "interceptions": 12,
    }
    output = add_per_90(row)
    assert output["goal_contributions_per_90"] == 3
    assert output["interceptions_per_90"] == 6
    assert all(column in output for column in DERIVED_COLUMNS)
    assert "goals_per_90" not in row
    assert add_per_90({"minutes": 90, "goals": 1})["goal_contributions_per_90"] is None


def test_zero_minutes_all_missing() -> None:
    output = add_per_90({"minutes": 0, "goals": 0, "assists": 0})
    assert all(output[column] is None for column in DERIVED_COLUMNS)
