# Database

Session 10 implements the V1 PostgreSQL layer. See [DATABASE.md](DATABASE.md) for
the actual schema, migrations, real import, money policy and tests. The broader
field lists below are roadmap context; unsupported statistics and current-club
inference are not part of the implemented schema.

## Goal

Store players, clubs, season statistics, market values, predictions, and model metadata.

Use PostgreSQL.

Production: Supabase PostgreSQL.

## Tables

### players

```text
id
external_id
name
normalized_name
date_of_birth
nationality
position
current_club_id
image_url
created_at
updated_at
```

### clubs

```text
id
external_id
name
league
country
badge_url
created_at
updated_at
```

### player_seasons

```text
id
player_id
club_id
season
age
position
appearances
starts
minutes
goals
assists
shots
shots_on_target
key_passes
passes
pass_accuracy
dribbles
tackles
interceptions
yellow_cards
red_cards
club_league_position
created_at
updated_at
```

### market_values

```text
id
player_id
value_eur
value_date
source
created_at
```

Do not overwrite historical values.

### predictions

```text
id
player_id nullable
model_run_id
input_snapshot JSONB
predicted_value_eur
observed_value_eur nullable
created_at
```

### model_runs

```text
id
model_name
model_version
dataset_version
mae
rmse
r2
feature_list JSONB
hyperparameters JSONB
trained_at
is_production
```

## ORM

Use SQLAlchemy + Alembic.

Suggested layout:

```text
backend/app/db/
├── base.py
├── session.py
└── models/
```

## Indexes

Recommended:

```text
players(normalized_name)
player_seasons(player_id, season)
market_values(player_id, value_date)
predictions(player_id, created_at)
model_runs(is_production)
```

## Data Import

Create a real import command:

```bash
python scripts/seed_database.py --input ml/data/processed/player_seasons.csv
```

Do not seed fake production data.

## Environment

```text
DATABASE_URL=
```

Never commit real secrets.

## Acceptance Criteria

- SQLAlchemy models exist
- Alembic works
- relationships are correct
- constraints exist
- import script exists
- model metadata can be stored
- local DB can be launched
- tests can use a test DB

## First Codex Prompt

```text
Read README.md and docs/DATABASE_README.md.

Implement only:
- SQLAlchemy schema
- session layer
- Alembic configuration
- initial migration
- database model tests

Create Player, Club, PlayerSeason, MarketValue, Prediction, and ModelRun.

Do not add API routes yet.
```
