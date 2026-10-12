"""Read credentials from the environment, or use a test-supplied connection."""

from alembic import context

from backend.app.db.base import Base
from backend.app.db.models import (  # noqa: F401
    Club,
    MarketValue,
    ModelRun,
    Player,
    PlayerSeason,
    Prediction,
)
from backend.app.db.session import create_db_engine

config = context.config


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(dialect_name="postgresql", target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    migrate(config.attributes["connection"])
else:
    engine = create_db_engine()
    try:
        with engine.connect() as connection:
            migrate(connection)
    finally:
        engine.dispose()
