"""HTTP concerns only; SQL and inference stay in services."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app import schemas
from backend.app.dependencies import get_runtime, get_session
from backend.app.services import model_service, player_service, prediction_service, ranking_service
from backend.app.services.model_service import RuntimeModel

router = APIRouter(
    prefix="/api/v1",
    responses={
        404: {"model": schemas.Error},
        422: {"model": schemas.Error},
        503: {"model": schemas.Error},
        500: {"model": schemas.Error},
    },
)
DB = Annotated[Session, Depends(get_session)]
Model = Annotated[RuntimeModel, Depends(get_runtime)]
SeasonQuery = Annotated[str | None, Query(pattern=r"^\d{4}/\d{2}$")]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
RankingLimit = Annotated[int, Query(ge=1, le=50)]


@router.get("/health", response_model=schemas.Health, tags=["health"], summary="Check dependencies")
def health(db: DB, runtime: Model):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok", "model": {"loaded": True, **runtime.identity}}


@router.get(
    "/players", response_model=schemas.PlayerPage, tags=["players"], summary="Search players"
)
def players(
    db: DB,
    search: Annotated[str, Query(max_length=200)] = "",
    limit: Limit = 20,
    offset: Offset = 0,
):
    return {
        "items": player_service.search_players(db, search, limit, offset),
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/players/{player_id}",
    response_model=schemas.PlayerDetail,
    tags=["players"],
    summary="Get profile; seasons and valuations newest first",
)
def player_detail(player_id: int, db: DB):
    return player_service.detail(db, player_id)


@router.get(
    "/players/{player_id}/prediction",
    response_model=schemas.PlayerEstimate,
    tags=["predictions"],
    summary="Estimate a stored season without persisting",
)
def player_prediction(player_id: int, db: DB, runtime: Model, season: SeasonQuery = None):
    return prediction_service.player_prediction(db, runtime, player_id, season)


@router.post(
    "/predictions",
    response_model=schemas.Estimate,
    tags=["predictions"],
    summary="Predict from exactly five V1 inputs; persistence is opt-in",
)
def prediction(inputs: schemas.Inputs, db: DB, runtime: Model, persist: bool = False):
    return prediction_service.predict(db, runtime, inputs, persist)


@router.post(
    "/players/{player_id}/simulate",
    response_model=schemas.Simulation,
    tags=["predictions"],
    summary="Apply hypothetical overrides; source stats never change",
)
def simulate(
    player_id: int,
    overrides: schemas.Overrides,
    db: DB,
    runtime: Model,
    season: SeasonQuery = None,
    persist: bool = False,
):
    return prediction_service.simulate(db, runtime, player_id, season, overrides, persist)


@router.get(
    "/models/current",
    response_model=schemas.CurrentModel,
    tags=["models"],
    summary="Current candidate and temporal OOF evidence, not all-data test metrics",
)
def current_model(db: DB, runtime: Model):
    return model_service.current_model(db, runtime)


@router.get(
    "/models",
    response_model=list[schemas.RegisteredModel],
    tags=["models"],
    summary="List registered model versions only",
)
def models(db: DB, limit: Limit = 20, offset: Offset = 0):
    return model_service.list_models(db, limit, offset)


@router.get(
    "/rankings/undervalued",
    response_model=schemas.Ranking,
    tags=["rankings"],
    summary="Largest positive model-estimated differences; not objective undervaluation",
)
def undervalued(db: DB, runtime: Model, season: SeasonQuery = None, limit: RankingLimit = 20):
    return ranking_service.rankings(db, runtime, season, limit, positive=True)


@router.get(
    "/rankings/overvalued",
    response_model=schemas.Ranking,
    tags=["rankings"],
    summary="Most negative model-estimated differences; not objective overvaluation",
)
def overvalued(db: DB, runtime: Model, season: SeasonQuery = None, limit: RankingLimit = 20):
    return ranking_service.rankings(db, runtime, season, limit, positive=False)
