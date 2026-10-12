"""One inference batch per season, with no writes or prediction-cache requirements."""

from sqlalchemy.orm import Session

from backend.app.core.errors import ServiceError

from .model_service import RuntimeModel
from .player_service import season_batch
from .prediction_service import season_inputs


def rankings(
    session: Session, runtime: RuntimeModel, season: str | None, limit: int, positive: bool
) -> dict:
    chosen, rows = season_batch(session, season)
    eligible, features = [], []
    for row, observed in rows:
        if observed is None:
            continue
        try:
            inputs = season_inputs(row)
        except ServiceError:
            continue
        eligible.append((row, observed))
        features.append(inputs)
    results = []
    predictions = runtime.predict(features) if features else []
    for (row, observed), predicted in zip(eligible, predictions, strict=True):
        difference = predicted - float(observed)
        if (positive and difference <= 0) or (not positive and difference >= 0):
            continue
        results.append(
            {
                "player_id": row.player_id,
                "player_name": row.player.name,
                "club": row.club.name if row.club else None,
                "position": row.position,
                "season": row.season,
                "observed_value_eur": observed,
                "predicted_value_eur": predicted,
                "difference_eur": difference,
            }
        )
    results.sort(key=lambda r: ((-1 if positive else 1) * r["difference_eur"], r["player_id"]))
    return {
        **runtime.identity,
        "season": chosen,
        "eligible_rows": len(eligible),
        "excluded_rows": len(rows) - len(eligible),
        "items": [{"rank": i, **row} for i, row in enumerate(results[:limit], 1)],
    }
