"""Public V1 contracts. All EUR amounts serialize as finite JSON numbers."""

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

Number = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]


class Inputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age: Number
    minutes: Number
    goals: Number = Field(description="Nonnegative integer-compatible goal count")
    assists: Number = Field(description="Nonnegative integer-compatible assist count")
    position: str | None = Field(description="Required key; null/unseen strings follow V1 encoding")

    @field_validator("goals", "assists")
    @classmethod
    def whole_count(cls, value: float) -> float:
        if not value.is_integer():
            raise ValueError("Count must be integer-compatible")
        return value


class Overrides(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age: Number | None = None
    minutes: Number | None = None
    goals: Number | None = None
    assists: Number | None = None
    position: str | None = None

    @field_validator("age", "minutes", "goals", "assists")
    @classmethod
    def not_null(cls, value):
        if value is None:
            raise ValueError("Numeric overrides cannot be null")
        return value

    @field_validator("goals", "assists")
    @classmethod
    def whole_count(cls, value):
        return Inputs.whole_count(value)


class PublicModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlayerSummary(PublicModel):
    id: int
    external_id: str
    name: str
    position: str | None
    nationality: str | None
    image_url: str | None
    latest_season: str | None = None
    latest_known_club: str | None = None


class PlayerProfile(PlayerSummary):
    date_of_birth: date | None


class PlayerPage(BaseModel):
    items: list[PlayerSummary]
    limit: int
    offset: int


class Season(PublicModel):
    season: str
    club: str | None
    age: int | None
    position: str | None
    appearances: int
    minutes: int
    goals: int
    assists: int
    yellow_cards: int
    red_cards: int
    goals_per_90: FiniteFloat | None
    assists_per_90: FiniteFloat | None
    goal_contributions_per_90: FiniteFloat | None
    clubs_in_season: int
    season_end_date: date


class ObservedValue(PublicModel):
    value_eur: FiniteFloat
    value_date: date
    source: str


class PlayerDetail(BaseModel):
    player: PlayerProfile
    seasons: list[Season]
    market_values: list[ObservedValue]


class ModelIdentity(BaseModel):
    model_name: str
    model_version: str


class Estimate(ModelIdentity):
    input: Inputs
    predicted_value_eur: FiniteFloat
    prediction_id: int | None = None


class PlayerEstimate(Estimate):
    player_id: int
    season: str
    observed_value_eur: FiniteFloat | None
    difference_eur: FiniteFloat | None = Field(description="Predicted minus observed EUR")


class Scenario(BaseModel):
    inputs: Inputs
    predicted_value_eur: FiniteFloat


class Simulation(ModelIdentity):
    player_id: int
    season: str
    baseline: Scenario
    simulation: Scenario
    difference_eur: FiniteFloat = Field(description="Simulated minus baseline prediction EUR")
    prediction_id: int | None = None


class RegisteredModel(ModelIdentity, PublicModel):
    model_type: str
    feature_list: list[str]
    evaluation_method: str
    mae: FiniteFloat | None
    rmse: FiniteFloat | None
    r2: FiniteFloat | None
    median_absolute_error: FiniteFloat | None
    is_production: bool


class CurrentModel(RegisteredModel):
    training_seasons: list[str]
    training_row_count: int
    evaluation_row_count: int
    limitations: list[str]


class RankingItem(BaseModel):
    rank: int
    player_id: int
    player_name: str
    club: str | None
    position: str | None
    season: str
    observed_value_eur: FiniteFloat
    predicted_value_eur: FiniteFloat
    difference_eur: FiniteFloat


class Ranking(ModelIdentity):
    season: str
    eligible_rows: int
    excluded_rows: int
    description: str = "Model-estimated difference only, not objective transfer value"
    items: list[RankingItem]


class HealthModel(ModelIdentity):
    loaded: bool


class Health(BaseModel):
    status: str
    database: str
    model: HealthModel


class Error(BaseModel):
    detail: str | list[dict]
