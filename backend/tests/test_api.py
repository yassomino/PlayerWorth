"""HTTP integration uses migrated TEST_DATABASE_URL schemas and deterministic models."""

import json
from datetime import date, datetime, timezone
from decimal import Decimal

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from backend.app.core.config import ROOT, Settings
from backend.app.db.models import Club, MarketValue, ModelRun, Player, PlayerSeason, Prediction
from backend.app.dependencies import get_session
from backend.app.main import create_app
from backend.app.services.model_service import RuntimeModel, load_runtime

INPUT = {"age": 24, "minutes": 3000, "goals": 15, "assists": 8, "position": "ST"}


class Stub:
    def __init__(self):
        self.calls = []

    def predict(self, frame):
        self.calls.append(frame.copy())
        return np.asarray(frame.goals * 10 + frame.assists - frame.age, dtype=float)


@pytest.fixture
def api(db_factory):
    metadata = {
        "model_name": "fixture",
        "model_version": "1",
        "dataset": {"sha256": "a" * 64},
        "features": list(INPUT),
        "hyperparameters": {},
        "training_seasons": ["2023/24"],
        "deployment_training_rows": 4,
        "evaluation": {"pooled": {"rows": 3}},
        "known_limitations": ["Synthetic test fixture"],
    }
    with db_factory.begin() as db:
        model = ModelRun(
            model_name="fixture",
            model_version="1",
            model_type="test",
            artifact_path="private/path",
            dataset_hash="a" * 64,
            feature_list=list(INPUT),
            hyperparameters={},
            mae=Decimal("12.25"),
            rmse=Decimal("15"),
            r2=Decimal("0.5"),
            median_absolute_error=Decimal("10"),
            evaluation_method="temporal out-of-fold backtest; NOT final-model test performance",
            trained_at=datetime.now(timezone.utc),
            is_production=True,
        )
        club = Club(external_id="club", name="Fixture club")
        db.add_all([model, club])
        ids = []
        for i, name, goals in [(0, "Alice Example", 1), (1, "Bob Example", 50), (2, "Carol", 30)]:
            player = Player(external_id=str(100 + i), name=name, normalized_name=name.casefold())
            db.add(player)
            db.flush()
            ids.append(player.id)
            seasons = [("2024/25", date(2025, 5, 25), goals, 100)]
            if i == 0:
                seasons.append(("2023/24", date(2024, 5, 19), 5, 20))
            for season, end, count, observed in seasons:
                db.add(
                    PlayerSeason(
                        player=player,
                        club=club,
                        season=season,
                        age=20,
                        position="ST",
                        appearances=30,
                        minutes=2000,
                        goals=count,
                        assists=0,
                        yellow_cards=0,
                        red_cards=0,
                        clubs_in_season=1,
                        season_end_date=end,
                    )
                )
                db.add(
                    MarketValue(
                        player=player, value_eur=observed, value_date=end, source="transfermarkt"
                    )
                )
        # Neither pre-season-end nor a different provider may override the target.
        db.add(
            MarketValue(
                player_id=ids[0],
                value_eur=99999,
                value_date=date(2025, 5, 24),
                source="transfermarkt",
            )
        )
        db.add(
            MarketValue(
                player_id=ids[0], value_eur=99999, value_date=date(2025, 5, 25), source="other"
            )
        )
    stub = Stub()
    runtime = RuntimeModel(stub, metadata)
    loads = []

    def loader(path):
        loads.append(path)
        return runtime

    app = create_app(Settings(), factory=db_factory, runtime_loader=loader)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, ids, db_factory, stub, app
    assert len(loads) == 1


def test_health_openapi_and_cors(api):
    client, _, _, _, _ = api
    result = client.get("/api/v1/health")
    assert result.status_code == 200
    assert result.json()["model"] == {"model_name": "fixture", "model_version": "1", "loaded": True}
    spec = client.get("/openapi.json").json()
    assert len(spec["paths"]) == 10
    assert all(path.startswith("/api/v1/") for path in spec["paths"])
    assert client.get("/docs").status_code == 200
    response = client.options(
        "/api/v1/predictions",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert (
        "access-control-allow-origin"
        not in client.get(
            "/api/v1/health", headers={"Origin": "https://unconfigured.example"}
        ).headers
    )


def test_search_pagination_and_detail(api):
    client, ids, *_ = api
    assert len(client.get("/api/v1/players?search=EXAMP").json()["items"]) == 2
    assert client.get("/api/v1/players?search=nobody").json()["items"] == []
    assert client.get("/api/v1/players?search=%25").json()["items"] == []
    result = client.get("/api/v1/players?limit=1&offset=1").json()
    assert result["items"][0]["id"] == ids[1]
    assert result["items"][0]["latest_known_club"] == "Fixture club"
    assert client.get("/api/v1/players?limit=101").status_code == 422
    assert client.get("/api/v1/players?offset=-1").status_code == 422
    detail = client.get(f"/api/v1/players/{ids[0]}").json()
    assert detail["player"]["id"] == ids[0]
    assert [s["season"] for s in detail["seasons"]] == ["2024/25", "2023/24"]
    assert isinstance(detail["market_values"][0]["value_eur"], float)
    assert client.get("/api/v1/players/999999").status_code == 404


def test_prediction_determinism_negative_and_unknown(api):
    client, _, factory, *_ = api
    data = {**INPUT, "goals": 0, "assists": 0, "position": "unseen"}
    first = client.post("/api/v1/predictions", json=data)
    assert first.status_code == 200
    assert first.json()["predicted_value_eur"] == -24
    assert first.json() == client.post("/api/v1/predictions", json=data).json()
    assert client.post("/api/v1/predictions", json={**data, "position": None}).status_code == 200
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0


@pytest.mark.parametrize("key", list(INPUT))
def test_missing_features(api, key):
    data = {k: v for k, v in INPUT.items() if k != key}
    assert api[0].post("/api/v1/predictions", json=data).status_code == 422


@pytest.mark.parametrize(
    "change",
    [
        {"age": -1},
        {"minutes": -1},
        {"goals": 0.5},
        {"assists": True},
        {"age": "24"},
        {"minutes": None},
        {"position": 10},
        {"extra": 1},
    ],
)
def test_invalid_features(api, change):
    assert api[0].post("/api/v1/predictions", json={**INPUT, **change}).status_code == 422


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_validation_is_safe_json(api, value):
    body = json.dumps(INPUT).replace('"age": 24', f'"age": {value}')
    response = api[0].post(
        "/api/v1/predictions", content=body, headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert "detail" in response.json()


def test_player_prediction_and_simulation(api):
    client, ids, factory, stub, _ = api
    path = f"/api/v1/players/{ids[0]}"
    latest = client.get(path + "/prediction").json()
    assert latest["season"] == "2024/25"
    assert latest["observed_value_eur"] == 100
    assert latest["difference_eur"] == -110
    assert client.get(path + "/prediction?season=2023/24").json()["predicted_value_eur"] == 30
    assert client.get(path + "/prediction?season=2020/21").status_code == 404
    assert client.post(path + "/simulate?season=2020/21", json={}).status_code == 404
    simulated = client.post(path + "/simulate", json={"goals": 20}).json()
    assert simulated["baseline"]["inputs"]["goals"] == 1
    assert simulated["simulation"]["inputs"]["goals"] == 20
    assert simulated["difference_eur"] == 190
    assert len(stub.calls[-1]) == 2
    assert client.post(path + "/simulate", json={"age": None}).status_code == 422
    assert client.post(path + "/simulate", json={"goals_per_90": 1}).status_code == 422
    assert client.post(path + "/simulate", json={"goals": 1.5}).status_code == 422
    with factory() as db:
        assert (
            db.scalar(
                select(PlayerSeason.goals).where(
                    PlayerSeason.player_id == ids[0], PlayerSeason.season == "2024/25"
                )
            )
            == 1
        )
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0


def test_registry_metadata_is_public(api):
    client = api[0]
    result = client.get("/api/v1/models/current").json()
    assert result["mae"] == 12.25 and result["evaluation_row_count"] == 3
    assert "temporal out-of-fold" in result["evaluation_method"]
    assert "artifact_path" not in result and "private" not in json.dumps(result)
    assert len(client.get("/api/v1/models").json()) == 1


def test_rankings_order_filter_limit_batch_and_no_writes(api):
    client, ids, factory, stub, _ = api
    before = len(stub.calls)
    result = client.get("/api/v1/rankings/undervalued?limit=1").json()
    assert len(stub.calls) == before + 1 and len(stub.calls[-1]) == 3
    assert result["season"] == "2024/25" and result["eligible_rows"] == 3
    assert result["items"][0]["player_id"] == ids[1]
    assert result["items"][0]["difference_eur"] == 380
    result = client.get("/api/v1/rankings/overvalued").json()
    assert result["items"][0]["player_id"] == ids[0]
    assert result["items"][0]["difference_eur"] == -110
    old = client.get("/api/v1/rankings/undervalued?season=2023/24").json()
    assert old["eligible_rows"] == 1 and old["items"][0]["difference_eur"] == 10
    assert client.get("/api/v1/rankings/undervalued?limit=51").status_code == 422
    assert client.get("/api/v1/rankings/undervalued?season=2000/01").status_code == 404
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0


def test_explicit_persistence(api):
    client, ids, factory, *_ = api
    inputs = {**INPUT, "goals": 0, "assists": 0}
    generic = client.post("/api/v1/predictions?persist=true", json=inputs).json()
    simulation = client.post(
        f"/api/v1/players/{ids[0]}/simulate?persist=true", json={"goals": 0}
    ).json()
    with factory() as db:
        records = list(db.scalars(select(Prediction).order_by(Prediction.id)))
        assert len(records) == 2
        assert records[0].id == generic["prediction_id"]
        assert records[0].player_id is None
        assert records[0].input_snapshot == inputs
        assert records[0].predicted_value_eur == Decimal("-24")
        assert records[0].model_run.model_name == "fixture"
        assert records[1].id == simulation["prediction_id"]
        assert records[1].input_snapshot["goals"] == 0
        assert records[1].observed_value_eur == Decimal("100")
        assert records[1].player_id == ids[0]
        assert all(r.prediction_type == "simulator" for r in records)


def test_failures_do_not_leak_internals(api, monkeypatch):
    client, _, _, stub, app = api

    def broken_predict(frame):
        raise RuntimeError("private/path secret")

    monkeypatch.setattr(stub, "predict", broken_predict)
    response = client.post("/api/v1/predictions", json=INPUT)
    assert response.status_code == 503 and "secret" not in response.text
    app.state.runtime.estimator = None
    assert client.get("/api/v1/health").status_code == 503

    def broken_db():
        raise OperationalError("private", {}, Exception("secret"))

    app.dependency_overrides[get_session] = broken_db
    response = client.get("/api/v1/players")
    assert response.status_code == 503 and "secret" not in response.text

    def unexpected():
        raise RuntimeError("secret")

    app.dependency_overrides[get_session] = unexpected
    response = client.get("/api/v1/players")
    assert response.status_code == 500 and "secret" not in response.text


def test_missing_model_fails_startup(tmp_path):
    with pytest.raises(RuntimeError, match="Cannot load configured"):
        with TestClient(create_app(Settings(model_pointer_path=tmp_path / "missing.json"))):
            pass


def test_real_frozen_model_http_integration(db_factory):
    pointer = ROOT / "ml/models/current_model.json"
    if not pointer.exists():
        pytest.skip("Real frozen V1 artifact is not installed")
    metadata = json.loads((pointer.parent / "playerworth_v1_metadata.json").read_text())
    pooled = metadata["evaluation"]["pooled"]
    with db_factory.begin() as db:
        db.add(
            ModelRun(
                model_name=metadata["model_name"],
                model_version=metadata["model_version"],
                model_type=metadata["model_type"],
                artifact_path="ml/models/playerworth_v1.joblib",
                dataset_hash=metadata["dataset"]["sha256"],
                feature_list=metadata["features"],
                hyperparameters=metadata["hyperparameters"],
                mae=Decimal(str(pooled["mae"])),
                rmse=Decimal(str(pooled["rmse"])),
                r2=Decimal(str(pooled["r2"])),
                median_absolute_error=Decimal(str(pooled["median_absolute_error_eur"])),
                evaluation_method=metadata["evaluation"]["scope"],
                trained_at=datetime.fromisoformat(metadata["training_timestamp_utc"]),
                is_production=True,
            )
        )
    with TestClient(create_app(Settings(), factory=db_factory)) as client:
        response = client.post("/api/v1/predictions", json=INPUT)
        assert response.status_code == 200
        assert response.json()["predicted_value_eur"] == 82459040.0
        assert client.get("/api/v1/models/current").json()["mae"] == pooled["mae"]


def test_config_rejects_wildcard(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    with pytest.raises(ValueError, match="explicit"):
        Settings.from_env()


def test_persistence_failure_rolls_back(api, monkeypatch):
    from sqlalchemy.orm import Session

    client, _, factory, *_ = api

    def failed_commit(self):
        raise OperationalError("private SQL", {}, Exception("secret"))

    monkeypatch.setattr(Session, "commit", failed_commit)
    response = client.post("/api/v1/predictions?persist=true", json=INPUT)
    assert response.status_code == 503 and "private" not in response.text
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Prediction)) == 0


def test_ranking_exclusions_and_inclusive_window(api):
    from datetime import timedelta

    client, ids, factory, *_ = api
    with factory.begin() as db:
        values = list(db.scalars(select(MarketValue).where(MarketValue.source == "transfermarkt")))
        for value in values:
            if value.value_date == date(2025, 5, 25):
                value.value_date += timedelta(days=45 if value.player_id == ids[1] else 46)
    result = client.get("/api/v1/rankings/undervalued").json()
    assert result["eligible_rows"] == 1 and result["excluded_rows"] == 2
    assert result["items"][0]["player_id"] == ids[1]
    assert client.get(f"/api/v1/players/{ids[0]}/prediction").json()["observed_value_eur"] is None
    with factory.begin() as db:
        row = db.scalar(
            select(PlayerSeason).where(
                PlayerSeason.player_id == ids[1], PlayerSeason.season == "2024/25"
            )
        )
        row.age = None
    assert client.get(f"/api/v1/players/{ids[1]}/prediction").status_code == 422
    assert client.get("/api/v1/rankings/undervalued").json()["eligible_rows"] == 0


def test_registry_missing_fails_startup(db_factory):
    runtime = RuntimeModel(Stub(), {"model_name": "not_registered", "model_version": "1"})
    with pytest.raises(RuntimeError, match="registry unavailable"):
        with TestClient(
            create_app(Settings(), factory=db_factory, runtime_loader=lambda path: runtime)
        ):
            pass


def test_pointer_identity_mismatch(tmp_path):
    (tmp_path / "current.json").write_text(
        json.dumps(
            {
                "model_name": "wrong",
                "model_version": "1",
                "artifact": "model.joblib",
                "metadata": "playerworth_v1_metadata.json",
            }
        )
    )
    (tmp_path / "playerworth_v1_metadata.json").write_text(
        json.dumps({"model_name": "playerworth_v1", "model_version": "1"})
    )
    with pytest.raises(ValueError, match="identity"):
        load_runtime(tmp_path / "current.json")
