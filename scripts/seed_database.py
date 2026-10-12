"""Run with python -m scripts.seed_database after alembic upgrade head."""

import argparse
import json
from pathlib import Path

from backend.app.db.import_data import ROOT, import_records, model_record, read_rows
from backend.app.db.session import create_db_engine, session_factory, session_scope


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "ml/data/processed/player_seasons.csv")
    parser.add_argument("--model-pointer", type=Path, default=ROOT / "ml/models/current_model.json")
    args = parser.parse_args()
    rows = read_rows(args.input)
    model = model_record(args.model_pointer, args.input)
    engine = create_db_engine()
    try:
        with session_scope(session_factory(engine)) as session:
            counts = import_records(session, rows, model)
        print(json.dumps({"input_rows": len(rows), "table_counts": counts}, indent=2))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
