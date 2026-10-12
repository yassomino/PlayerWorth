# Project Setup

Session 1 created the repository skeleton. Session 2 added the generic data pipeline.
Session 2.5 integrates the local Transfermarkt CSVs; see [TRANSFERMARKT_DATA.md](TRANSFERMARKT_DATA.md)
for the real dataset and reproduction command.

## Structure

- `frontend/`: Next.js and TypeScript configuration, with empty `app/`, `components/`, `lib/api/`, and `public/` directories.
- `backend/app/`: Python package with reserved `core/`, `db/`, `schemas/`, `routes/`, and `services/` directories. No FastAPI application yet.
- `backend/tests/`: reserved for backend tests; `ml/tests/`: data-pipeline tests.
- `ml/data_pipeline/`: ingestion, normalization, matching, per-90 helpers, dataset building, and CLI stages.
- `ml/data/raw/` and `ml/data/processed/`: local input and output datasets.
- `ml/notebooks/`: exploratory analysis workspace.
- `ml/preprocessing/`: reserved preprocessing package.
- `ml/models/`: generated model artifacts and evaluation outputs.
- `ml/train.py` and `ml/evaluate.py`: train and reload/evaluate the Session 3 linear baseline.
- `ml/baseline.py`: shared four-feature selection, temporal split, metrics, and interpretation helpers.
- `scripts/`: four data-pipeline CLI wrappers; use `python -m scripts.<script_name>`.
- `pyproject.toml`: Python metadata, pinned numerical/ML dependencies, and pytest/Ruff settings.
- `docker-compose.yml`: empty service mapping; database configuration belongs to Session 5.
- `.env.example`: existing empty configuration template, preserved unchanged.

Empty directories contain `.gitkeep` files so they can be tracked when Git is initialized.
Local environment files, datasets, model artifacts, dependencies, and caches are ignored.
Processed Markdown documentation can be tracked; generated datasets and metrics cannot be mistaken for source files.

## Python

Use Python 3.11 or newer. Create a local environment from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the pinned provider dependencies and validation tools:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

## Frontend

Use Node.js 20.9 or newer, as required by the [Next.js installation guide](https://nextjs.org/docs/app/getting-started/installation).
Node.js 24 is the setup environment used for this milestone.

```powershell
cd frontend
npm ci
npm run typecheck
```

On Windows, use `npm.cmd` if PowerShell blocks the `npm.ps1` wrapper.
The dependency versions and lockfile pin the initial configuration.
`dev`, `build`, and `start` scripts are reserved for Session 7: they are not usable as an application until the root layout and pages are implemented.
Tailwind, shadcn/ui, charts, navigation, and API clients also belong to that later session.

## Current milestone

**Session 3 — Linear Regression:** the four-feature temporal baseline, saved Pipeline, and
evaluation artifacts are complete. Read [LINEAR_REGRESSION.md](LINEAR_REGRESSION.md) to
understand the actual model and its limitations before proceeding. Session 4 has not begun.
