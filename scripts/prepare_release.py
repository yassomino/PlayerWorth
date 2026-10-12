"""Stage an allowlisted backend release; never copy raw exports or local secrets."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED = (
    "Dockerfile",
    ".dockerignore",
    "railway.json",
    "requirements-runtime.txt",
    "alembic.ini",
    "scripts/seed_database.py",
    "backend/migrations/script.py.mako",
    "ml/models/current_model.json",
    "ml/models/playerworth_v1.joblib",
    "ml/models/playerworth_v1_metadata.json",
    "ml/data/processed/player_seasons.csv",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def release_files(root: Path) -> list[Path]:
    files = [root / name for name in FIXED]
    for folder in ("backend", "ml"):
        files.extend(
            p
            for p in (root / folder).rglob("*.py")
            if p.relative_to(root / folder).parts[0]
            not in {"tests", "data", "models", "evaluation", "__pycache__"}
        )
    for path in files:
        if (
            not path.is_file()
            or path.is_symlink()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise ValueError(f"Missing or unsafe release file: {path.relative_to(root)}")
    return sorted(set(files))


def prepare(root: Path, output: Path) -> dict[str, str]:
    if output.exists():
        raise ValueError("Output already exists; choose a new release directory")
    pointer = json.loads((root / "ml/models/current_model.json").read_text())
    if pointer["artifact"] != "playerworth_v1.joblib" or pointer["metadata"] != (
        "playerworth_v1_metadata.json"
    ):
        raise ValueError("Unexpected frozen artifact pointer")
    metadata = json.loads((root / "ml/models/playerworth_v1_metadata.json").read_text())
    # Validate the frozen source before staging; runtime also verifies the model hash.
    from backend.app.services.model_service import load_runtime

    load_runtime(root / "ml/models/current_model.json")
    if digest(root / "ml/data/processed/player_seasons.csv") != metadata["dataset"]["sha256"]:
        raise ValueError("Processed dataset hash differs from frozen model provenance")
    files = release_files(root)
    manifest = {p.relative_to(root).as_posix(): digest(p) for p in files}
    output.mkdir(parents=True)
    for source in files:
        destination = output / source.relative_to(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if digest(destination) != manifest[source.relative_to(root).as_posix()]:
            raise ValueError("Release copy hash mismatch")
    (output / "release_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/release")
    args = parser.parse_args()
    manifest = prepare(ROOT, args.output)
    print(f"Staged {len(manifest)} verified files in {args.output}")


if __name__ == "__main__":
    main()
