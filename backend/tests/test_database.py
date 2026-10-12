"""Small synthetic PostgreSQL fixtures; no full real dataset or ML fitting."""

import csv
import hashlib
import json
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from backend.app.db.import_data import decimal_value, import_records, read_rows, table_counts
from backend.app.db.models import Club, MarketValue, ModelRun, Player, PlayerSeason, Prediction
from backend.app.db.session import create_db_engine, session_scope


@pytest.fixture
def records(tmp_path):
    row = dict(
        player_id="123",
        player_name="Test Player",
        club_id="456",
        club="Test Club",
        season="2023/24",
        date_of_birth="2000-01-01",
        age="24",
        position="ST",
        position_raw="Attack",
        sub_position_raw="Centre-Forward",
        appearances="2",
        minutes="180",
        goals="1",
        assists="0",
        yellow_cards="0",
        red_cards="0",
        goals_per_90="0.5",
        assists_per_90="0",
        goal_contributions_per_90="0.5",
        season_end_date="2024-05-19",
        clubs_in_season="2",
        market_value_eur="10000000",
        market_value_date="2024-05-20",
    )
    path = tmp_path / "fixture.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    return read_rows(path)


@pytest.fixture
def metadata():
    return dict(
        model_name="fixture",
        model_version="1",
        model_type="synthetic",
        artifact_path="ml/models/fixture.joblib",
        dataset_hash="a" * 64,
        feature_list=["age", "minutes", "goals", "assists", "position"],
        hyperparameters={"n_estimators": 63},
        mae=Decimal("10.25"),
        rmse=Decimal("12.5"),
        r2=Decimal("0.5"),
        median_absolute_error=None,
        evaluation_method="temporal out-of-fold backtest; NOT final-model test performance",
        trained_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_production=True,
    )


def test_import_rerun_relationships_and_metadata(db_factory, records, metadata):
    with session_scope(db_factory) as session:
        first = import_records(session, records, metadata)
    with session_scope(db_factory) as session:
        assert import_records(session, records, metadata) == first
        assert first == dict(
            players=1, clubs=1, player_seasons=1, market_values=1, model_runs=1, predictions=0
        )
        player = session.scalar(select(Player))
        assert player.external_id == "123" and player.id != 123
        assert player.normalized_name == "test player"
        assert player.image_url is None and player.nationality is None
        assert player.seasons[0].club.external_id == "456"
        assert player.seasons[0].clubs_in_season == 2
        assert player.market_values[0].value_eur == Decimal("10000000")
        model = session.scalar(select(ModelRun))
        assert model.mae == Decimal("10.25") and model.feature_list == metadata["feature_list"]
        assert model.evaluation_method == metadata["evaluation_method"]
        assert session.scalar(select(Club)).badge_url is None
        assert session.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0001"


def test_raw_negative_prediction_money_and_relationships(db_factory, records, metadata):
    value = Decimal("-102108.937500000001")
    with session_scope(db_factory) as session:
        import_records(session, records, metadata)
        player = session.scalar(select(Player))
        model = session.scalar(select(ModelRun))
        session.add(
            Prediction(
                player=player,
                model_run=model,
                input_snapshot={"age": 24},
                predicted_value_eur=value,
                observed_value_eur=Decimal("0.1"),
                prediction_type="stored_player",
            )
        )
    with db_factory() as session:
        prediction = session.scalar(select(Prediction))
        assert prediction.predicted_value_eur == value
        assert prediction.observed_value_eur == Decimal("0.1")
        assert prediction.player.predictions == [prediction]
        assert prediction.model_run.predictions == [prediction]


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("player_seasons", "minutes", -1),
        ("player_seasons", "goals", -1),
        ("player_seasons", "assists", -1),
        ("market_values", "value_eur", -1),
    ],
)
def test_nonnegative_constraints(db_factory, records, metadata, table, column, value):
    with session_scope(db_factory) as session:
        import_records(session, records, metadata)
    with pytest.raises(IntegrityError), session_scope(db_factory) as session:
        session.execute(text(f"UPDATE {table} SET {column} = :value"), {"value": value})


@pytest.mark.parametrize("observed,kind", [(-1, "simulator"), (0, "invalid")])
def test_prediction_constraints(db_factory, records, metadata, observed, kind):
    with session_scope(db_factory) as session:
        import_records(session, records, metadata)
    with pytest.raises(IntegrityError), session_scope(db_factory) as session:
        model = session.scalar(select(ModelRun))
        session.add(
            Prediction(
                model_run=model,
                input_snapshot={},
                predicted_value_eur=-1,
                observed_value_eur=observed,
                prediction_type=kind,
            )
        )


@pytest.mark.parametrize("model", [Player, Club, PlayerSeason, MarketValue, ModelRun])
def test_unique_keys(db_factory, records, metadata, model):
    with session_scope(db_factory) as session:
        import_records(session, records, metadata)
    with pytest.raises(IntegrityError), session_scope(db_factory) as session:
        record = session.scalar(select(model))
        session.add(
            model(
                **{
                    c.name: getattr(record, c.name)
                    for c in model.__table__.columns
                    if c.name != "id"
                }
            )
        )


def test_conflicts_roll_back_and_history_appends(db_factory, records, metadata):
    with session_scope(db_factory) as session:
        initial = import_records(session, records, metadata)
    changed = [{**records[0], "player_name": "Must roll back", "market_value_eur": Decimal("1")}]
    with pytest.raises(ValueError, match="Historical valuation conflict"):
        with session_scope(db_factory) as session:
            import_records(session, changed, metadata)
    with db_factory() as session:
        assert table_counts(session) == initial
        assert session.scalar(select(Player)).name == "Test Player"
    with session_scope(db_factory) as session:
        later = [{**records[0], "market_value_date": date(2024, 5, 21)}]
        assert import_records(session, later, metadata)["market_values"] == 2


@pytest.mark.parametrize("model", [Player, Club])
def test_parent_deletion_is_restricted(db_factory, records, metadata, model):
    with session_scope(db_factory) as session:
        import_records(session, records, metadata)
    with pytest.raises(IntegrityError), session_scope(db_factory) as session:
        record = session.scalar(select(model))
        _ = record.seasons  # Loaded relationships must not be silently detached either.
        session.delete(record)


def test_model_version_cannot_be_rewritten(db_factory, records, metadata):
    with session_scope(db_factory) as session:
        import_records(session, records, metadata)
    with pytest.raises(ValueError, match="Registered model version"):
        with session_scope(db_factory) as session:
            import_records(session, records, {**metadata, "mae": Decimal("1")})


def test_money_conversion_and_configuration(monkeypatch):
    assert decimal_value(0.1) == Decimal("0.1")
    with pytest.raises(ValueError):
        decimal_value(float("nan"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        create_db_engine()
    with pytest.raises(ValueError, match="PostgreSQL"):
        create_db_engine("sqlite://")


@pytest.mark.parametrize("tamper", [None, "artifact", "dataset", "pointer"])
def test_frozen_metadata_registration(tmp_path, monkeypatch, tamper):
    from backend.app.db import import_data

    monkeypatch.setattr(import_data, "ROOT", tmp_path)
    artifact = tmp_path / "model.joblib"
    artifact.write_bytes(b"synthetic artifact; not loaded as a model")
    dataset = tmp_path / "data.csv"
    dataset.write_text("synthetic data")
    meta = {
        "model_name": "playerworth_v1",
        "model_version": "1.0.0",
        "model_type": "fixture",
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "dataset": {"sha256": hashlib.sha256(dataset.read_bytes()).hexdigest()},
        "evaluation": {
            "scope": "temporal out-of-fold backtest; NOT final-model test performance",
            "pooled": {"mae": 12.5},
        },
        "features": ["age"],
        "hyperparameters": {},
        "training_timestamp_utc": "2026-01-01T00:00:00+00:00",
    }
    (tmp_path / "metadata.json").write_text(json.dumps(meta))
    pointer = tmp_path / "current.json"
    pointer.write_text(
        json.dumps(
            {
                "model_name": "playerworth_v1",
                "model_version": "1.0.0",
                "artifact": "model.joblib",
                "metadata": "metadata.json",
            }
        )
    )
    if tamper == "artifact":
        artifact.write_bytes(b"changed")
    elif tamper == "dataset":
        dataset.write_text("changed")
    elif tamper == "pointer":
        pointer.write_text(pointer.read_text().replace("1.0.0", "2.0.0"))
    if tamper:
        with pytest.raises(ValueError):
            import_data.model_record(pointer, dataset)
    else:
        result = import_data.model_record(pointer, dataset)
        assert result["mae"] == Decimal("12.5")
        assert result["rmse"] is None  # Absent evidence is never invented.
        assert result["artifact_path"] == "model.joblib"


@pytest.mark.parametrize(
    "change",
    [
        {"minutes": "-1"},
        {"goals": "0.5"},
        {"market_value_date": "2024-05-18"},
        {"market_value_eur": "NaN"},
        {"season": "2023/2024"},
    ],
)
def test_invalid_source_is_rejected(tmp_path, records, change):
    path = tmp_path / "invalid.csv"
    row = {**records[0], **change}
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=row)
        writer.writeheader()
        writer.writerow(row)
    with pytest.raises(ValueError):
        read_rows(path)


def test_duplicate_source_is_rejected(tmp_path, records):
    path = tmp_path / "duplicate.csv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=records[0])
        writer.writeheader()
        writer.writerows(records * 2)
    with pytest.raises(ValueError, match="Duplicate player-season"):
        read_rows(path)
