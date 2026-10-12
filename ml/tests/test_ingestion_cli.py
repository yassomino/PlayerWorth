import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from ml.data_pipeline.cli import load_mapping, merge_envelopes
from ml.data_pipeline.dataset import normalize_rows
from ml.data_pipeline.ingestion import ingest_csv, read_csv


def make_source(tmp_path: Path, row: dict, kind: str) -> tuple[Path, Path]:
    csv_path = tmp_path / f"{kind}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    manifest = {
        "source_name": "Synthetic test fixture only",
        "url": "https://example.invalid/test",
        "retrieval_date": "2025-01-01",
        "license": "Test fixture",
        "usage_restrictions": "Only for unit tests",
        "id_namespace": row["id_namespace"],
        "fields_used": list(row),
        "kind": kind,
        "source_type": "static_csv",
    }
    manifest_path = tmp_path / f"{kind}.manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return csv_path, manifest_path


def test_ingestion_tracks_original_bytes(tmp_path: Path, stats_row: dict) -> None:
    csv_path, manifest = make_source(tmp_path, stats_row, "statistics")
    before = csv_path.read_bytes()
    rows, provenance = ingest_csv(csv_path, manifest)
    assert rows[0]["player_id"] == "001"
    assert provenance["sha256"] == hashlib.sha256(before).hexdigest()
    assert csv_path.read_bytes() == before


def test_manifest_is_required_and_validated(tmp_path: Path, stats_row: dict) -> None:
    csv_path, manifest = make_source(tmp_path, stats_row, "statistics")
    payload = json.loads(manifest.read_text())
    del payload["license"]
    manifest.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="license"):
        ingest_csv(csv_path, manifest)


@pytest.mark.parametrize("contents", ["", "id,id\n1,2\n", "id,name\n1\n", "id\n1,2\n"])
def test_malformed_csv(tmp_path: Path, contents: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(contents)
    with pytest.raises(ValueError):
        read_csv(path)


def test_empty_csv_not_ingested(tmp_path: Path, stats_row: dict) -> None:
    csv_path, manifest = make_source(tmp_path, stats_row, "statistics")
    csv_path.write_text(",".join(stats_row) + "\n")
    with pytest.raises(ValueError, match="no records"):
        ingest_csv(csv_path, manifest)


def test_conflicting_crosswalk_rejected(tmp_path: Path) -> None:
    path = tmp_path / "mapping.csv"
    path.write_text(
        "statistics_namespace,statistics_player_id,valuation_namespace,valuation_player_id\na,1,b,2\na,1,b,3\n"
    )
    with pytest.raises(ValueError, match="Conflicting mapping"):
        load_mapping(path)


def test_full_cli_pipeline(
    tmp_path: Path, stats_row: dict, value_row: dict, policies: dict
) -> None:
    root = Path(__file__).resolve().parents[2]
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps({"policies": {key: asdict(value) for key, value in policies.items()}})
    )

    def run(module: str, *arguments: str | Path) -> subprocess.CompletedProcess:
        completed = subprocess.run(
            [sys.executable, "-m", f"scripts.{module}", *map(str, arguments)],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        return completed

    for row, kind in ((stats_row, "statistics"), (value_row, "valuations")):
        csv_path, manifest = make_source(tmp_path, row, kind)
        raw = tmp_path / f"{kind}.raw.json"
        normalized = tmp_path / f"{kind}.normalized.json"
        run("ingest_players", "--csv", csv_path, "--manifest", manifest, "--output", raw)
        run("normalize_players", "--input", raw, "--config", config, "--output", normalized)
    merged = tmp_path / "merged.json"
    run(
        "merge_sources",
        "--statistics",
        tmp_path / "statistics.normalized.json",
        "--valuations",
        tmp_path / "valuations.normalized.json",
        "--config",
        config,
        "--output",
        merged,
    )
    run("build_training_dataset", "--input", merged, "--output", tmp_path / "output")
    report = json.loads((tmp_path / "output/cleaning_report.json").read_text())
    assert report["final_rows"] == 1
    assert len(report["sources"]) == 2
    assert report["upstream_normalization"]["statistics"]["input_rows"] == 1
    assert report["merge_artifact_sha256"] == hashlib.sha256(merged.read_bytes()).hexdigest()


def test_cli_requires_inputs() -> None:
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "scripts.build_training_dataset"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "required" in result.stderr


def test_merge_preserves_upstream_counts_and_rejections(
    stats_row: dict, value_row: dict, policies: dict
) -> None:
    config = {"policies": {key: asdict(value) for key, value in policies.items()}}
    raw = [stats_row, stats_row, dict(stats_row, player_id="invalid", minutes="-1")]
    rows, issues, duplicates = normalize_rows(raw, "statistics")
    stats = {
        "rows": rows,
        "provenance": {"kind": "statistics"},
        "normalization": {
            "input_rows": 3,
            "issues": issues,
            "duplicates_removed": duplicates,
            "configuration": config,
        },
    }
    values = {"rows": [value_row], "provenance": {"kind": "valuations"}}
    result = merge_envelopes(stats, values, config, {})
    assert result.report["input_rows"]["statistics"] == 3
    assert result.report["duplicates_removed"]["statistics"] == 1
    assert result.report["rejected_statistics_rows"] == 1
    assert len(result.report["issues"]) == 1
    with pytest.raises(ValueError, match="Alias configuration changed"):
        merge_envelopes(stats, values, dict(config, club_aliases={"test club": "canonical"}), {})
