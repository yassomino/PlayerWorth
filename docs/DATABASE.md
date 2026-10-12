# PlayerWorth database — Session 10

PostgreSQL, SQLAlchemy 2 and Alembic store source records and model metadata.
The database does not train models. V1 ML files, processed data and the inference
contract remain unchanged. No API or frontend is implemented in this session.

## Schema

```text
players (internal id; unique external_id = Transfermarkt ID)
  |--< player_seasons >-- clubs (internal id; unique external_id)
  |--< market_values
  |--< predictions >-- model_runs
```

All six tables have generated BIGINT internal primary keys and timezone-aware
creation timestamps. Players, clubs and player-seasons also have update timestamps.
Foreign keys use RESTRICT; ORM relationships never cascade-delete history or
silently null out loaded child records. Deleting referenced parents fails.

| Table | Purpose and uniqueness |
|---|---|
| players | Name, normalized search name, DOB, nullable nationality/position/image; unique provider ID |
| clubs | Name, EPL context, country, nullable badge; unique provider ID |
| player_seasons | Historical primary club and real statistics; unique internal player ID + season |
| market_values | Observed EUR/date/source; unique internal player ID + date + source |
| model_runs | Artifact/version, dataset hash, JSONB features/parameters, evaluation evidence; unique name + version |
| predictions | Nullable player, required model run, JSONB input snapshot, raw output and optional observation/type |

Seasons retain `2021/22` formatting. PlayerSeason includes age, mapped/raw/sub-position,
appearances, minutes, goals, assists, cards, three existing per-90 rates, season end
and `clubs_in_season`. Missing rates/age/positions can be NULL; absent richer metrics
are not fabricated. Counts are nonnegative and club count is positive.

Unique constraints create indexes for external IDs and player-season identity.
Additional indexes cover normalized player names, valuation player/date, prediction
player/creation date, and production-candidate model selection. Name normalization
reuses the existing Unicode/case-folding helper; names are not identity keys.

## Money and prediction history

All money uses PostgreSQL unconstrained **NUMERIC**, mapped to Python Decimal.
This deliberately uses the permitted NUMERIC alternative to BIGINT: the frozen
inference contract returns fractional, sometimes negative euros. Rounding to integer
euros would discard raw output. No fixed scale silently rounds it. Use
`decimal_value(value)` at the persistence boundary to convert via decimal text,
not `Decimal(float)`. Existing binary floating-point inference cannot be made more
precise by storage; this preserves its decimal representation without further rounding.

Observed values must be finite and nonnegative; predictions must be finite but can
be negative. Display rounding/clipping is outside this layer. Prediction types are
`stored_player`, `simulator`, and `batch_ranking`. Input snapshots preserve the
features used for each future request, independent of changing season records.
The seed command generates no predictions; the table starts empty.

## Local setup with Docker

Install the pinned dependencies from the repository root:

```powershell
python -m pip install -r requirements-dev.txt
```

Copy `.env.example` to `.env`, set a local-only POSTGRES_PASSWORD and corresponding
DATABASE_URL. Compose reads `.env`; Python/Alembic deliberately read process
environment variables, so also set DATABASE_URL in your shell (or environment manager).
URL-encode special characters in connection-string credentials.

```powershell
docker compose up -d db
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@localhost:5432/playerworth'
python -m alembic upgrade head
python -m alembic current
python -m scripts.seed_database
python -m scripts.seed_database  # safe rerun
```

Compose uses PostgreSQL 17, loopback-only published port and a persistent named
volume. It requires a password rather than supplying a shared default. `docker
compose down` stops the service without deleting data; do not add `-v` unless you
intend to erase the volume. A normal installed PostgreSQL server works equally well.
Do not run migrations with production credentials during local development.

## Migration and sessions

`alembic.ini` points to `backend/migrations/`. Revision `0001` explicitly creates
all six tables, constraints and indexes; runtime `create_all()` is unnecessary.
The downgrade removes these tables and their history, so use it only deliberately.
`python -m alembic check` detects ORM/migration drift on the target database.

`create_db_engine()` reads DATABASE_URL lazily, accepts normal PostgreSQL URLs and
uses psycopg. `session_factory(engine)` creates sessions. `session_scope(factory)`
commits successful work, rolls back failures, and closes the session. Dispose the
engine when a CLI exits; a future server can reuse one engine. Imports open no DB
connections automatically. No FastAPI dependency or route is added.

## Real import and model registration

The default CLI reads `ml/data/processed/player_seasons.csv` and
`ml/models/current_model.json`. Optional `--input` and `--model-pointer` select paths.
The selected data must match the frozen metadata hash; the artifact hash and
pointer identity must also match. Artifact paths stored in PostgreSQL are relative
to the repository. The artifact remains a file, not a database blob.

The importer validates the canonical seasons, numeric fields, unique player-season
keys and inclusive 0..45-day post-season valuation rule before writing. It sorts
chronologically and uses each player's latest available row for display metadata.
Historical positions remain on each season. Identity always uses Transfermarkt IDs.
Names and positions are snapshot metadata, not independently verified history.
Nationality, image and badge URLs remain NULL because the processed CSV lacks them.
Club league/country reflect this dataset's English Premier League scope.

All writes share one transaction and an advisory transaction lock serializes this
importer. Players/clubs/seasons use deterministic PostgreSQL upserts; reruns may
refresh update timestamps but not create duplicate identities. Season valuations
are appended only for unseen player/date/source keys (`source=transfermarkt`). A
different amount for an existing key raises an error and rolls back the whole
import, rather than replacing history. Records absent from a later import are not
deleted. This is not a complete raw valuation archive.

V1 registration stores the accepted **temporal out-of-fold backtest** metrics from
`evaluation.pooled`, including MAE, RMSE, R² and median absolute error. These came
from 2,103 OOF predictions, not the all-data model's 2,594 training observations.
`evaluation_method` explicitly retains the metadata's scope caveat. Missing metrics
stay NULL. Re-registering identical metadata is a no-op; changed metadata under an
existing name/version raises an error. Future changes need a new model version.
`is_production=True` marks the selected V1 production candidate; it does not mean
an API deployment has happened. Future promotion/demotion is not automated here.

Multi-club seasons keep the upstream primary club and `clubs_in_season` count
(60 real rows have more than one club). Season totals include all participating
EPL clubs; the CSV does not provide their full breakdown. This database does not
invent transfer history or infer a player's current club from an old season.

## Tests and Session 10 validation

Create a separate empty test database with your local PostgreSQL administrator:

```powershell
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" playerworth_test'
$env:TEST_DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@localhost:5432/playerworth_test'
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Each DB test migrates an isolated random schema in TEST_DATABASE_URL and drops only
that schema afterward. Tests never fall back to DATABASE_URL or hosted production.
Without TEST_DATABASE_URL, integration tests explicitly skip; pure validation tests
still run. PostgreSQL is required to validate JSONB, NUMERIC, constraints and upserts;
SQLite is not substituted. Test fixtures are small and synthetic.

This workstation lacked Docker/PostgreSQL on PATH. Validation used EDB's official
portable PostgreSQL 17 binaries in `%LOCALAPPDATA%\PlayerWorth`, with password
authentication, loopback-only port 55432, persistent local data and a separate test
database. Local credentials are in ignored `.local/database-env.ps1`; load them with
`. ./.local/database-env.ps1`. They are not in tracked configuration. To stop/start
this local instance:

```powershell
$pgRoot = Join-Path $env:LOCALAPPDATA 'PlayerWorth'
& "$pgRoot\pgsql\bin\pg_ctl.exe" -D "$pgRoot\data" stop
& "$pgRoot\pgsql\bin\pg_ctl.exe" -D "$pgRoot\data" -l "$pgRoot\postgres.log" start
```

Real import and rerun counts: 1,139 players, 27 clubs, 2,594 player-seasons, 2,594
market values, one model run and zero predictions. Natural-key duplicate counts
are zero. Frozen data/model/evaluation files are hash-checked before/after this task.
Docker Compose execution itself is unverified on this workstation.
Validation completed with 185 passing tests (28 database/import tests), Ruff lint
and formatting passing, migration `0001` at head with no ORM drift, and all 53
snapshotted frozen data/model/evaluation files unchanged.

## Supabase later

Use Supabase's PostgreSQL connection string with a SQLAlchemy psycopg scheme and
the host's required TLS parameters (for example `?sslmode=require`). Keep credentials
in deployment secrets. Run Alembic via a direct/session connection with DDL rights;
pooler transaction-mode compatibility should be checked separately before use.
No Supabase client API, auth, RLS policy or frontend access is configured. Keep these
tables private to the backend role; do not expose the public schema through a hosted
data API without reviewing grants/RLS. Hosted migration/deployment is not validated
in this local-only milestone.
