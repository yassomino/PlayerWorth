"""V1 feature selection, optional explicit persistence and hypothetical simulation."""

from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.core.errors import ServiceError
from backend.app.db.import_data import decimal_value
from backend.app.db.models import PlayerSeason, Prediction
from backend.app.schemas import Inputs, Overrides

from .model_service import RuntimeModel, registered_model
from .player_service import observed_value, selected_season


def season_inputs(row: PlayerSeason) -> dict:
    try:
        return Inputs.model_validate(
            {key: getattr(row, key) for key in Inputs.model_fields}
        ).model_dump()
    except ValidationError:
        raise ServiceError(422, "Stored season lacks valid V1 inputs") from None


def persist_prediction(
    session: Session,
    runtime: RuntimeModel,
    inputs: dict,
    value: float,
    player_id: int | None = None,
    observed=None,
) -> int:
    record = registered_model(session, runtime)
    prediction = Prediction(
        player_id=player_id,
        model_run_id=record.id,
        input_snapshot=inputs,
        predicted_value_eur=decimal_value(value),
        observed_value_eur=observed,
        prediction_type="simulator",
    )
    session.add(prediction)
    session.flush()
    identity = prediction.id
    # Commit before returning HTTP success, so storage failures cannot follow a 200.
    session.commit()
    return identity


def predict(session: Session, runtime: RuntimeModel, inputs: Inputs, persist: bool) -> dict:
    data = inputs.model_dump()
    value = runtime.predict([data])[0]
    prediction_id = persist_prediction(session, runtime, data, value) if persist else None
    return {
        **runtime.identity,
        "input": data,
        "predicted_value_eur": value,
        "prediction_id": prediction_id,
    }


def player_prediction(
    session: Session, runtime: RuntimeModel, player_id: int, season: str | None
) -> dict:
    row = selected_season(session, player_id, season)
    inputs = season_inputs(row)
    value = runtime.predict([inputs])[0]
    observed = observed_value(session, row)
    return {
        **runtime.identity,
        "player_id": player_id,
        "season": row.season,
        "input": inputs,
        "predicted_value_eur": value,
        "observed_value_eur": observed,
        "difference_eur": value - float(observed) if observed is not None else None,
    }


def simulate(
    session: Session,
    runtime: RuntimeModel,
    player_id: int,
    season: str | None,
    overrides: Overrides,
    persist: bool,
) -> dict:
    row = selected_season(session, player_id, season)
    baseline = season_inputs(row)
    simulated = Inputs.model_validate(
        {**baseline, **overrides.model_dump(exclude_unset=True)}
    ).model_dump()
    original, changed = runtime.predict([baseline, simulated])
    prediction_id = (
        persist_prediction(
            session, runtime, simulated, changed, player_id, observed_value(session, row)
        )
        if persist
        else None
    )
    return {
        **runtime.identity,
        "player_id": player_id,
        "season": row.season,
        "baseline": {"inputs": baseline, "predicted_value_eur": original},
        "simulation": {"inputs": simulated, "predicted_value_eur": changed},
        "difference_eur": changed - original,
        "prediction_id": prediction_id,
    }
