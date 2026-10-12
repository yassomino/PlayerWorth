"""The six V1 tables. NUMERIC preserves fractional and negative model outputs."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Created, Timestamps


class Player(Timestamps, Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(Text)
    normalized_name: Mapped[str] = mapped_column(Text, index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(Text)
    position: Mapped[str | None] = mapped_column(String(32))
    image_url: Mapped[str | None] = mapped_column(Text)
    seasons: Mapped[list["PlayerSeason"]] = relationship(
        back_populates="player", passive_deletes="all"
    )
    market_values: Mapped[list["MarketValue"]] = relationship(
        back_populates="player", passive_deletes="all"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="player", passive_deletes="all"
    )


class Club(Timestamps, Base):
    __tablename__ = "clubs"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(Text)
    league: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(Text)
    badge_url: Mapped[str | None] = mapped_column(Text)
    seasons: Mapped[list["PlayerSeason"]] = relationship(
        back_populates="club", passive_deletes="all"
    )


class PlayerSeason(Timestamps, Base):
    __tablename__ = "player_seasons"
    __table_args__ = (
        UniqueConstraint("player_id", "season"),
        CheckConstraint("season ~ '^[0-9]{4}/[0-9]{2}$'", name="season_format"),
        CheckConstraint("clubs_in_season >= 1", name="club_count"),
        *(
            CheckConstraint(f"{column} >= 0", name=f"{column}_nonnegative")
            for column in (
                "age",
                "appearances",
                "minutes",
                "goals",
                "assists",
                "yellow_cards",
                "red_cards",
                "goals_per_90",
                "assists_per_90",
                "goal_contributions_per_90",
            )
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"))
    club_id: Mapped[int | None] = mapped_column(ForeignKey("clubs.id", ondelete="RESTRICT"))
    season: Mapped[str] = mapped_column(String(7))
    age: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[str | None] = mapped_column(String(32))
    position_raw: Mapped[str | None] = mapped_column(Text)
    sub_position_raw: Mapped[str | None] = mapped_column(Text)
    appearances: Mapped[int] = mapped_column(Integer)
    minutes: Mapped[int] = mapped_column(Integer)
    goals: Mapped[int] = mapped_column(Integer)
    assists: Mapped[int] = mapped_column(Integer)
    yellow_cards: Mapped[int] = mapped_column(Integer)
    red_cards: Mapped[int] = mapped_column(Integer)
    goals_per_90: Mapped[Decimal | None] = mapped_column(Numeric)
    assists_per_90: Mapped[Decimal | None] = mapped_column(Numeric)
    goal_contributions_per_90: Mapped[Decimal | None] = mapped_column(Numeric)
    season_end_date: Mapped[date] = mapped_column(Date)
    clubs_in_season: Mapped[int] = mapped_column(Integer)
    player: Mapped[Player] = relationship(back_populates="seasons")
    club: Mapped[Club | None] = relationship(back_populates="seasons")


class MarketValue(Created, Base):
    __tablename__ = "market_values"
    __table_args__ = (
        UniqueConstraint("player_id", "value_date", "source"),
        Index("ix_market_values_player_date", "player_id", "value_date"),
        CheckConstraint(
            "value_eur >= 0 AND value_eur < 'Infinity'::numeric", name="observed_value"
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"))
    value_eur: Mapped[Decimal] = mapped_column(Numeric)
    value_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(64))
    player: Mapped[Player] = relationship(back_populates="market_values")


class ModelRun(Created, Base):
    __tablename__ = "model_runs"
    __table_args__ = (UniqueConstraint("model_name", "model_version"),)
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(128))
    model_version: Mapped[str] = mapped_column(String(64))
    model_type: Mapped[str] = mapped_column(Text)
    artifact_path: Mapped[str] = mapped_column(Text)
    dataset_hash: Mapped[str] = mapped_column(String(64))
    feature_list: Mapped[list] = mapped_column(JSONB)
    hyperparameters: Mapped[dict] = mapped_column(JSONB)
    mae: Mapped[Decimal | None] = mapped_column(Numeric)
    rmse: Mapped[Decimal | None] = mapped_column(Numeric)
    r2: Mapped[Decimal | None] = mapped_column(Numeric)
    median_absolute_error: Mapped[Decimal | None] = mapped_column(Numeric)
    evaluation_method: Mapped[str] = mapped_column(Text)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_production: Mapped[bool] = mapped_column(Boolean, server_default=false(), index=True)
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="model_run", passive_deletes="all"
    )


class Prediction(Created, Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_player_created", "player_id", "created_at"),
        CheckConstraint(
            "prediction_type IN ('stored_player', 'simulator', 'batch_ranking')", name="type"
        ),
        CheckConstraint(
            "observed_value_eur >= 0 AND observed_value_eur < 'Infinity'::numeric", name="observed"
        ),
        CheckConstraint(
            "predicted_value_eur > '-Infinity'::numeric "
            "AND predicted_value_eur < 'Infinity'::numeric",
            name="finite_prediction",
        ),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id", ondelete="RESTRICT"))
    model_run_id: Mapped[int] = mapped_column(ForeignKey("model_runs.id", ondelete="RESTRICT"))
    input_snapshot: Mapped[dict] = mapped_column(JSONB)
    predicted_value_eur: Mapped[Decimal] = mapped_column(Numeric)
    observed_value_eur: Mapped[Decimal | None] = mapped_column(Numeric)
    prediction_type: Mapped[str] = mapped_column(String(32))
    player: Mapped[Player | None] = relationship(back_populates="predictions")
    model_run: Mapped[ModelRun] = relationship(back_populates="predictions")
