"""Request-scoped sessions reuse the lifespan-created factory."""

from fastapi import Request

from backend.app.core.errors import ServiceError


def get_session(request: Request):
    # Session.close rolls back uncommitted work even when a service raises.
    with request.app.state.session_factory() as session:
        yield session


def get_runtime(request: Request):
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None or runtime.estimator is None:
        raise ServiceError(503, "Model unavailable")
    return runtime
