"""Read explicitly supplied local CSV exports and record their provenance.

TODO: implement source-specific adapters only after datasets/APIs and usage rights
are selected. This module does not download, scrape, or generate football data.
"""

import csv
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .normalization import Row, iso_date


def hash_file(path: Path) -> str:
    """Hash source bytes without loading a large export into memory."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_csv(path: Path) -> list[Row]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        if not headers or any(not key for key in headers) or len(set(headers)) != len(headers):
            raise ValueError("CSV requires nonempty, unique column names")
        rows = []
        for line, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV row {line} does not match the header width")
            rows.append(dict(row))
        return rows


def ingest_csv(path: Path, manifest_path: Path) -> tuple[list[Row], dict[str, Any]]:
    """Read canonical columns; retain the original source export unchanged."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in (
        "source_name",
        "url",
        "retrieval_date",
        "license",
        "usage_restrictions",
        "id_namespace",
    ):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            raise ValueError(f"Source manifest requires {key}")
    if urlparse(manifest["url"]).scheme not in {"http", "https"}:
        raise ValueError("Source URL must be http(s)")
    manifest["retrieval_date"] = iso_date(manifest["retrieval_date"])
    if manifest.get("kind") not in {"statistics", "valuations"}:
        raise ValueError("Source manifest kind must be statistics or valuations")
    if manifest.get("source_type") not in {"static_csv", "api_export"}:
        raise ValueError("source_type must be static_csv or api_export")
    fields = manifest.get("fields_used")
    if (
        not isinstance(fields, list)
        or not fields
        or not all(isinstance(v, str) and v for v in fields)
    ):
        raise ValueError("fields_used must be a nonempty list of canonical column names")
    rows = read_csv(path)
    if not rows:
        raise ValueError("Source CSV has no records")
    if not set(fields).issubset(rows[0]):
        raise ValueError("Manifest fields_used contains columns missing from the CSV")
    for row in rows:
        if row.get("id_namespace") and row["id_namespace"] != manifest["id_namespace"]:
            raise ValueError("Row ID namespace conflicts with source manifest")
        row["id_namespace"] = manifest["id_namespace"]
    provenance = dict(manifest, sha256=hash_file(path), rows=len(rows))
    return rows, provenance
