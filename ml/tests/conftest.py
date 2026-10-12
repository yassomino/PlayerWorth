"""Invented data exclusively for tests, never production source records."""

import pytest

from ml.data_pipeline.matching import ValuationPolicy


@pytest.fixture
def stats_row() -> dict:
    return {
        "id_namespace": "test_stats",
        "player_id": "001",
        "player_name": "Test Player",
        "season": "2022/23",
        "club": "Test Club",
        "competition": "EPL",
        "statistics_as_of": "2023-05-31",
        "date_of_birth": "2000-01-01",
        "age": "23",
        "position": "CM",
        "minutes": "900",
        "goals": "2",
        "assists": "3",
        "appearances": "12",
        "starts": "10",
        "shots": "10",
        "shots_on_target": "4",
    }


@pytest.fixture
def value_row() -> dict:
    return {
        "id_namespace": "test_values",
        "player_id": "V1",
        "player_name": "Test Player",
        "season": "2022/23",
        "club": "Test Club",
        "date_of_birth": "2000-01-01",
        "market_value_eur": "1000",
        "currency": "EUR",
        "market_value_date": "2023-06-01",
    }


@pytest.fixture
def policies() -> dict[str, ValuationPolicy]:
    # Synthetic dates to test boundaries; not an adopted football valuation policy.
    return {
        "2022/23": ValuationPolicy("2023-05-31", "2023-06-01", "2023-06-30", "2023-08-01", "latest")
    }
