"""Transactional import of the processed Transfermarkt dataset and frozen V1 metadata."""

import csv
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ml.data_pipeline.ingestion import hash_file
from ml.data_pipeline.normalization import normalize_name, normalize_season

from .models import Club, MarketValue, ModelRun, Player, PlayerSeason, Prediction

ROOT = Path(__file__).resolve().parents[3]
COUNTS = ("appearances", "minutes", "goals", "assists", "yellow_cards", "red_cards")
RATES = ("goals_per_90", "assists_per_90", "goal_contributions_per_90")


def decimal_value(value: str | int | float | Decimal) -> Decimal:
    """Use decimal text, never Decimal(float), and never silently round/clamp."""
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("Expected a finite numeric value")
    return result


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Dataset is empty")
    seen = set()
    for row in rows:
        for key in ("player_id", "player_name", "club_id", "club"):
            if not row[key].strip():
                raise ValueError(f"Missing {key}")
        if normalize_season(row["season"]) != row["season"]:
            raise ValueError("Use canonical YYYY/YY seasons")
        identity = row["player_id"], row["season"]
        if identity in seen:
            raise ValueError(f"Duplicate player-season: {identity}")
        seen.add(identity)
        for key in (*COUNTS, "clubs_in_season", "age"):
            if key == "age" and not row[key]:
                row[key] = None
                continue
            value = decimal_value(row[key])
            if value < 0 or value != value.to_integral_value():
                raise ValueError(f"Invalid nonnegative integer {key}")
            row[key] = int(value)
        if row["clubs_in_season"] < 1:
            raise ValueError("clubs_in_season must be positive")
        for key in (*RATES, "market_value_eur"):
            row[key] = decimal_value(row[key]) if row[key] else None
            if row[key] is not None and row[key] < 0:
                raise ValueError(f"Negative {key}")
        if row["market_value_eur"] is None:
            raise ValueError("Missing observed market value")
        for key in ("date_of_birth", "season_end_date", "market_value_date"):
            row[key] = date.fromisoformat(row[key]) if row[key] else None
        if not row["season_end_date"] or not row["market_value_date"]:
            raise ValueError("Missing season/valuation date")
        offset = (row["market_value_date"] - row["season_end_date"]).days
        if not 0 <= offset <= 45:
            raise ValueError("Valuation must be within 0..45 days after season end")
        for key in ("position", "position_raw", "sub_position_raw"):
            row[key] = row[key] or None
    return sorted(rows, key=lambda r: (r["season"], r["player_id"]))


def model_record(pointer_path: Path, dataset_path: Path) -> dict:
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    folder = pointer_path.resolve().parent
    artifact = (folder / pointer["artifact"]).resolve()
    metadata_path = (folder / pointer["metadata"]).resolve()
    if artifact.parent != folder or metadata_path.parent != folder:
        raise ValueError("Model pointer must use sibling filenames")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if hash_file(artifact) != metadata["artifact_sha256"]:
        raise ValueError("Frozen model artifact hash mismatch")
    if hash_file(dataset_path) != metadata["dataset"]["sha256"]:
        raise ValueError("Dataset hash differs from frozen model metadata")
    if any(pointer[k] != metadata[k] for k in ("model_name", "model_version")):
        raise ValueError("Model pointer/metadata identity mismatch")
    evaluation = metadata["evaluation"]
    if "temporal out-of-fold" not in evaluation["scope"]:
        raise ValueError("Expected temporal out-of-fold evaluation evidence")
    pooled = evaluation["pooled"]
    result = {
        "model_name": metadata["model_name"],
        "model_version": metadata["model_version"],
        "model_type": metadata["model_type"],
        "artifact_path": artifact.relative_to(ROOT).as_posix(),
        "dataset_hash": metadata["dataset"]["sha256"],
        "feature_list": metadata["features"],
        "hyperparameters": metadata["hyperparameters"],
        "evaluation_method": evaluation["scope"],
        "trained_at": datetime.fromisoformat(metadata["training_timestamp_utc"]),
        "is_production": True,
    }
    for column, key in (
        ("mae", "mae"),
        ("rmse", "rmse"),
        ("r2", "r2"),
        ("median_absolute_error", "median_absolute_error_eur"),
    ):
        result[column] = decimal_value(pooled[key]) if key in pooled else None
    return result


def upsert(session: Session, model, records: list[dict], keys: list[str]) -> None:
    if not records:
        return
    # Bound statement size, including large historical imports.
    for start in range(0, len(records), 500):
        statement = insert(model).values(records[start : start + 500])
        updates = {k: statement.excluded[k] for k in records[0] if k not in keys}
        if "updated_at" in model.__table__.c:
            updates["updated_at"] = func.now()
        session.execute(statement.on_conflict_do_update(index_elements=keys, set_=updates))


def import_records(session: Session, rows: list[dict], model: dict) -> dict[str, int]:
    """Caller owns transaction. Serialize imports to avoid conflicting valuation races."""
    session.execute(text("SELECT pg_advisory_xact_lock(710102594)"))
    players, clubs = {}, {}
    for row in rows:  # Already sorted chronologically: latest available display metadata wins.
        players[row["player_id"]] = {
            "external_id": row["player_id"],
            "name": row["player_name"],
            "normalized_name": normalize_name(row["player_name"]),
            "date_of_birth": row["date_of_birth"],
            "position": row["position"],
        }
        clubs[row["club_id"]] = {
            "external_id": row["club_id"],
            "name": row["club"],
            "league": "English Premier League",
            "country": "England",
        }
    upsert(session, Player, list(players.values()), ["external_id"])
    upsert(session, Club, list(clubs.values()), ["external_id"])
    player_ids = dict(session.execute(select(Player.external_id, Player.id)).all())
    club_ids = dict(session.execute(select(Club.external_id, Club.id)).all())
    seasons, valuations = [], {}
    for row in rows:
        player_id = player_ids[row["player_id"]]
        seasons.append(
            {
                **{
                    k: row[k]
                    for k in (
                        *COUNTS,
                        *RATES,
                        "season",
                        "age",
                        "position",
                        "position_raw",
                        "sub_position_raw",
                        "season_end_date",
                        "clubs_in_season",
                    )
                },
                "player_id": player_id,
                "club_id": club_ids[row["club_id"]],
            }
        )
        key = player_id, row["market_value_date"], "transfermarkt"
        value = row["market_value_eur"]
        if key in valuations and valuations[key] != value:
            raise ValueError("Conflicting source valuation amounts")
        valuations[key] = value
    upsert(session, PlayerSeason, seasons, ["player_id", "season"])
    existing = {
        (v.player_id, v.value_date, v.source): v.value_eur
        for v in session.scalars(select(MarketValue))
    }
    for key, value in valuations.items():
        if key in existing and existing[key] != value:
            raise ValueError(f"Historical valuation conflict for {key}; no values overwritten")
    new_values = [
        {"player_id": k[0], "value_date": k[1], "source": k[2], "value_eur": v}
        for k, v in valuations.items()
        if k not in existing
    ]
    if new_values:
        session.execute(insert(MarketValue), new_values)
    current = session.scalar(
        select(ModelRun).where(
            ModelRun.model_name == model["model_name"],
            ModelRun.model_version == model["model_version"],
        )
    )
    if current is None:
        session.add(ModelRun(**model))
    elif any(getattr(current, key) != value for key, value in model.items()):
        raise ValueError(
            "Registered model version differs; use a new version instead of overwriting"
        )
    session.flush()
    return table_counts(session)


def table_counts(session: Session) -> dict[str, int]:
    return {
        m.__tablename__: session.scalar(select(func.count()).select_from(m))
        for m in (Player, Club, PlayerSeason, MarketValue, ModelRun, Prediction)
    }
