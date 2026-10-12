from pathlib import Path

import pytest

from scripts.prepare_release import FIXED, release_files


def fixture_tree(root: Path) -> None:
    for name in (*FIXED, "backend/app/main.py", "ml/inference.py"):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")


def test_release_allowlist_excludes_secrets_raw_data_and_other_models(tmp_path):
    fixture_tree(tmp_path)
    for name in (
        ".env",
        "ml/data/raw/players.csv",
        "ml/models/experimental.joblib",
        "backend/tests/test_api.py",
        ".local/secret.py",
        "frontend/.env.local",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("must not ship")
    names = {p.relative_to(tmp_path).as_posix() for p in release_files(tmp_path)}
    assert names == set(FIXED) | {"backend/app/main.py", "ml/inference.py"}


def test_missing_frozen_artifact_stops_release(tmp_path):
    fixture_tree(tmp_path)
    (tmp_path / "ml/models/playerworth_v1.joblib").unlink()
    with pytest.raises(ValueError, match="Missing or unsafe"):
        release_files(tmp_path)
