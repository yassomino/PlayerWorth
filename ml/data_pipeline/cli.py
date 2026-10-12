"""Command-line stages. Run wrappers with `python -m scripts.<stage>`."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .dataset import BuildResult, build_dataset, normalize_rows, write_dataset
from .ingestion import ingest_csv, read_csv
from .matching import IdMapping, ValuationPolicy


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)


def load_mapping(path: Path | None) -> IdMapping:
    if path is None:
        return {}
    result: IdMapping = {}
    for row in read_csv(path):
        fields = (
            "statistics_namespace",
            "statistics_player_id",
            "valuation_namespace",
            "valuation_player_id",
        )
        if any(not isinstance(row.get(field), str) or not row[field].strip() for field in fields):
            raise ValueError(f"Mapping requires nonempty columns: {fields}")
        source = (str(row[fields[0]]).strip(), str(row[fields[1]]).strip())
        target = (str(row[fields[2]]).strip(), str(row[fields[3]]).strip())
        if source in result and result[source] != target:
            raise ValueError(f"Conflicting mapping for {source}")
        result[source] = target
    return result


def merge_envelopes(
    statistics: dict[str, Any],
    valuations: dict[str, Any],
    config: dict[str, Any],
    mapping: IdMapping,
) -> BuildResult:
    for envelope, expected in ((statistics, "statistics"), (valuations, "valuations")):
        if envelope["provenance"]["kind"] != expected:
            raise ValueError(f"Expected a {expected} source envelope")
        upstream = envelope.get("normalization")
        if upstream:
            for alias_key in ("club_aliases", "position_aliases"):
                if upstream["configuration"].get(alias_key, {}) != config.get(alias_key, {}):
                    raise ValueError(
                        "Alias configuration changed; normalize the original inputs again"
                    )
    policies = {season: ValuationPolicy(**policy) for season, policy in config["policies"].items()}
    result = build_dataset(
        statistics["rows"],
        valuations["rows"],
        policies=policies,
        mapping=mapping,
        club_aliases=config.get("club_aliases"),
        position_aliases=config.get("position_aliases"),
    )
    result.report["sources"] = [statistics["provenance"], valuations["provenance"]]
    result.report["configuration"] = config
    result.report["reviewed_mapping"] = [
        {"statistics_id": list(source), "valuation_id": list(target)}
        for source, target in sorted(mapping.items())
    ]
    result.report["upstream_normalization"] = {
        "statistics": statistics.get("normalization"),
        "valuations": valuations.get("normalization"),
    }
    for kind, envelope in (("statistics", statistics), ("valuations", valuations)):
        if upstream := envelope.get("normalization"):
            result.report["input_rows"][kind] = upstream["input_rows"]
            result.report["duplicates_removed"][kind] += upstream["duplicates_removed"]
            result.report["issues"].extend(upstream["issues"])
    result.report["rejected_statistics_rows"] = (
        result.report["input_rows"]["statistics"]
        - result.report["duplicates_removed"]["statistics"]
        - result.report["final_rows"]
    )
    return result


def main(stage: str) -> None:
    parser = argparse.ArgumentParser(description=f"PlayerWorth data pipeline: {stage}")
    if stage == "ingest":
        parser.add_argument("--csv", type=Path, required=True)
        parser.add_argument("--manifest", type=Path, required=True)
    elif stage == "build":
        parser.add_argument("--provider", choices=["generic", "transfermarkt"], default="generic")
        parser.add_argument("--input", type=Path)
        parser.add_argument("--raw-dir", type=Path, default=Path("ml/data/raw"))
        parser.add_argument("--seasons", nargs="+")
        parser.add_argument("--days-before", type=int, choices=[0], default=0)
        parser.add_argument("--days-after", type=int, default=45)
    elif stage == "normalize":
        parser.add_argument("--input", type=Path, required=True)
    elif stage == "merge":
        parser.add_argument("--statistics", type=Path, required=True)
        parser.add_argument("--valuations", type=Path, required=True)
        parser.add_argument("--mapping", type=Path)
    else:
        raise ValueError(f"Unknown pipeline stage: {stage}")
    if stage in {"normalize", "merge"}:
        parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New JSON file, or output directory for the build stage",
    )
    args = parser.parse_args()
    if stage == "build" and args.provider == "generic" and args.input is None:
        parser.error("--input is required for the generic builder")
    try:
        if stage == "build" and args.provider == "transfermarkt":
            from .providers.transfermarkt import DEFAULT_SEASONS, Config, run, write_result

            config = Config(
                seasons=tuple(args.seasons or DEFAULT_SEASONS),
                days_before=args.days_before,
                days_after=args.days_after,
            )
            result = run(args.raw_dir, config)
            write_result(result, args.output)
            print(
                json.dumps(
                    {
                        "final_rows": result.report["final_rows"],
                        "per_season": result.report["per_season_final_counts"],
                    }
                )
            )
        elif stage == "ingest":
            rows, provenance = ingest_csv(args.csv, args.manifest)
            write_json(args.output, {"rows": rows, "provenance": provenance})
        elif stage == "normalize":
            envelope, config = read_json(args.input), read_json(args.config)
            if "normalization" in envelope:
                raise ValueError("Input is already normalized; use the original ingested envelope")
            rows, issues, duplicates = normalize_rows(
                envelope["rows"],
                envelope["provenance"]["kind"],
                club_aliases=config.get("club_aliases"),
                position_aliases=config.get("position_aliases"),
            )
            write_json(
                args.output,
                dict(
                    envelope,
                    rows=rows,
                    normalization={
                        "input_rows": len(envelope["rows"]),
                        "issues": issues,
                        "duplicates_removed": duplicates,
                        "configuration": config,
                    },
                ),
            )
        elif stage == "merge":
            result = merge_envelopes(
                read_json(args.statistics),
                read_json(args.valuations),
                read_json(args.config),
                load_mapping(args.mapping),
            )
            write_json(args.output, {"rows": result.rows, "report": result.report})
        else:
            payload = read_json(args.input)
            # The writer checks schema, duplicate identities, targets, and derived features.
            result = BuildResult(payload["rows"], payload["report"])
            result.report["merge_artifact_sha256"] = hashlib.sha256(
                args.input.read_bytes()
            ).hexdigest()
            write_dataset(result, args.output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"{stage} failed: {error}\n")


if __name__ == "__main__":
    raise SystemExit("Use python -m scripts.ingest_players (or the other stage wrappers).")
