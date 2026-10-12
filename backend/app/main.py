"""Run python -m backend.app.main, or uvicorn backend.app.main:app --reload."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import Settings
from backend.app.core.errors import ServiceError
from backend.app.db.session import create_db_engine, session_factory
from backend.app.routes import router
from backend.app.services.model_service import load_runtime, registered_model

logger = logging.getLogger("playerworth.api")


def create_app(
    settings: Settings | None = None, *, factory=None, runtime_loader=load_runtime
) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
        engine = None
        try:
            try:
                runtime = runtime_loader(config.model_pointer_path)
            except Exception as exc:
                logger.error("Model startup failed (%s)", type(exc).__name__)
                raise RuntimeError(
                    "Cannot load configured PlayerWorth model; check pointer/artifact"
                ) from None
            try:
                if factory is None:
                    engine = create_db_engine(config.database_url)
                app.state.session_factory = factory or session_factory(engine)
                with app.state.session_factory() as session:
                    record = registered_model(session, runtime)
                    runtime.model_run_id = record.id
            except Exception as exc:
                logger.error("Database/registry startup failed (%s)", type(exc).__name__)
                raise RuntimeError(
                    "Database/current model registry unavailable; check setup"
                ) from None
            app.state.runtime = runtime
            logger.info("Loaded model %s version %s", *runtime.identity.values())
            yield
        finally:
            app.state.runtime = None
            if engine is not None:
                engine.dispose()

    app = FastAPI(
        title="PlayerWorth API",
        version="1.0.0",
        lifespan=lifespan,
        description="End-of-season model estimates, not true transfer values.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(router)

    @app.exception_handler(ServiceError)
    async def service_error(request: Request, exc: ServiceError):
        return JSONResponse(status_code=exc.status, content={"detail": exc.message})

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Never echo arbitrary request content or non-JSON NaN/Infinity in error responses.
        errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        logger.error("Database request failed (%s)", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Database unavailable"})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logger.error("Unhandled request error (%s)", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    config = Settings.from_env()
    logging.basicConfig(level=logging.INFO)
    uvicorn.run("backend.app.main:app", host=config.api_host, port=config.api_port)
