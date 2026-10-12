"""One verified runtime model per application process, no automatic fallback."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import ServiceError
from backend.app.db.models import ModelRun
from backend.app.schemas import CurrentModel, RegisteredModel
from ml import inference

logger = logging.getLogger(__name__)


@dataclass
class RuntimeModel:
    estimator: Any
    metadata: dict
    model_run_id: int | None = None

    @property
    def identity(self) -> dict:
        return {key: self.metadata[key] for key in ("model_name", "model_version")}

    def predict(self, rows: list[dict]) -> list[float]:
        if self.estimator is None:
            raise ServiceError(503, "Model unavailable")
        try:
            return inference.predict_batch(rows, model=self.estimator).tolist()
        except Exception as exc:
            logger.error("Model prediction failed (%s)", type(exc).__name__)
            raise ServiceError(503, "Model prediction unavailable") from None


def load_runtime(pointer_path: Path) -> RuntimeModel:
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    folder = pointer_path.resolve().parent
    artifact = (folder / pointer["artifact"]).resolve()
    metadata_path = (folder / pointer["metadata"]).resolve()
    if artifact.parent != folder or metadata_path != artifact.with_name(
        "playerworth_v1_metadata.json"
    ):
        raise ValueError("Pointer must reference sibling V1 artifact and metadata")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if any(pointer[k] != metadata[k] for k in ("model_name", "model_version")):
        raise ValueError("Pointer and metadata identity mismatch")
    # Existing loader verifies artifact hash and frozen feature contract.
    return RuntimeModel(inference.load_model(artifact), metadata)


def registered_model(session: Session, runtime: RuntimeModel) -> ModelRun:
    record = session.scalar(
        select(ModelRun).where(
            ModelRun.model_name == runtime.metadata["model_name"],
            ModelRun.model_version == runtime.metadata["model_version"],
        )
    )
    if record is None or not record.is_production:
        raise ServiceError(503, "Current model is not registered as a production candidate")
    if (
        record.dataset_hash != runtime.metadata["dataset"]["sha256"]
        or record.feature_list != runtime.metadata["features"]
        or record.hyperparameters != runtime.metadata["hyperparameters"]
    ):
        raise ServiceError(503, "Registered model configuration mismatch")
    return record


def current_model(session: Session, runtime: RuntimeModel) -> CurrentModel:
    record = registered_model(session, runtime)
    return CurrentModel(
        **RegisteredModel.model_validate(record).model_dump(),
        training_seasons=runtime.metadata["training_seasons"],
        training_row_count=runtime.metadata["deployment_training_rows"],
        evaluation_row_count=runtime.metadata["evaluation"]["pooled"]["rows"],
        limitations=runtime.metadata["known_limitations"],
    )


def list_models(session: Session, limit: int, offset: int) -> list[ModelRun]:
    return list(
        session.scalars(
            select(ModelRun)
            .order_by(ModelRun.created_at.desc(), ModelRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
