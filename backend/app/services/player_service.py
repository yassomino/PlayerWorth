"""Bounded searches, explicit season ordering and shared season-target alignment."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.app.core.errors import ServiceError
from backend.app.db.models import Club, MarketValue, Player, PlayerSeason
from backend.app.schemas import PlayerDetail, PlayerProfile, PlayerSummary, Season
from ml.data_pipeline.normalization import normalize_name


def search_players(session: Session, search: str, limit: int, offset: int) -> list[dict]:
    latest_id = (
        select(PlayerSeason.id)
        .where(PlayerSeason.player_id == Player.id)
        .order_by(PlayerSeason.season.desc())
        .limit(1)
        .correlate(Player)
        .scalar_subquery()
    )
    query = (
        select(Player, PlayerSeason.season, Club.name)
        .outerjoin(PlayerSeason, PlayerSeason.id == latest_id)
        .outerjoin(Club, Club.id == PlayerSeason.club_id)
    )
    if search.strip():
        query = query.where(
            Player.normalized_name.contains(normalize_name(search), autoescape=True)
        )
    rows = session.execute(
        query.order_by(Player.normalized_name, Player.id).limit(limit).offset(offset)
    )
    return [
        {
            **PlayerSummary.model_validate(p).model_dump(),
            "latest_season": season,
            "latest_known_club": club,
        }
        for p, season, club in rows
    ]


def detail(session: Session, player_id: int) -> PlayerDetail:
    player = session.scalar(
        select(Player)
        .where(Player.id == player_id)
        .options(
            selectinload(Player.seasons).joinedload(PlayerSeason.club),
            selectinload(Player.market_values),
        )
    )
    if player is None:
        raise ServiceError(404, "Player not found")
    seasons = sorted(player.seasons, key=lambda s: s.season, reverse=True)
    profile = PlayerProfile.model_validate(player)
    if seasons:
        profile.latest_season = seasons[0].season
        profile.latest_known_club = seasons[0].club.name if seasons[0].club else None
    return PlayerDetail(
        player=profile,
        seasons=[
            Season(
                **{key: getattr(s, key) for key in Season.model_fields if key != "club"},
                club=s.club.name if s.club else None,
            )
            for s in seasons
        ],
        market_values=sorted(
            player.market_values, key=lambda v: (v.value_date, v.id), reverse=True
        ),
    )


def selected_season(session: Session, player_id: int, season: str | None) -> PlayerSeason:
    if session.get(Player, player_id) is None:
        raise ServiceError(404, "Player not found")
    query = select(PlayerSeason).where(PlayerSeason.player_id == player_id)
    if season is not None:
        query = query.where(PlayerSeason.season == season)
    result = session.scalar(query.order_by(PlayerSeason.season.desc()).limit(1))
    if result is None:
        raise ServiceError(404, "Player season not found")
    return result


def observed_subquery():
    """Earliest Transfermarkt observation within the frozen 0..45-day window."""
    return (
        select(MarketValue.value_eur)
        .where(
            MarketValue.player_id == PlayerSeason.player_id,
            MarketValue.source == "transfermarkt",
            MarketValue.value_date >= PlayerSeason.season_end_date,
            MarketValue.value_date <= PlayerSeason.season_end_date + 45,
        )
        .order_by(MarketValue.value_date, MarketValue.id)
        .limit(1)
        .correlate(PlayerSeason)
        .scalar_subquery()
    )


def observed_value(session: Session, row: PlayerSeason):
    return session.scalar(
        select(observed_subquery()).select_from(PlayerSeason).where(PlayerSeason.id == row.id)
    )


def season_batch(session: Session, season: str | None):
    chosen = season or session.scalar(select(func.max(PlayerSeason.season)))
    if chosen is None:
        raise ServiceError(404, "No player seasons available")
    rows = session.execute(
        select(PlayerSeason, observed_subquery())
        .where(PlayerSeason.season == chosen)
        .options(joinedload(PlayerSeason.player), joinedload(PlayerSeason.club))
        .order_by(PlayerSeason.player_id)
    ).all()
    if not rows:
        raise ServiceError(404, "Season not found")
    return chosen, rows
