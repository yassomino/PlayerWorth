"""Build one validated modeling row per source player ID and season."""

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .features import DERIVED_COLUMNS, add_per_90
from .matching import IdMapping, PlayerMatcher, ValuationPolicy, identity, select_valuation
from .normalization import COUNTS, Row, iso_date, normalize_record, normalize_season, number

OUTPUT_COLUMNS = (
    "player_id",
    "player_name",
    "season",
    "club",
    "age",
    "position",
    *COUNTS,
    "pass_accuracy",
    "club_league_position",
    "market_value_eur",
    "market_value_date",
    *DERIVED_COLUMNS,
)


@dataclass
class BuildResult:
    rows: list[Row]
    report: dict[str, Any]


def normalize_rows(
    rows: list[Row],
    kind: str,
    *,
    club_aliases: dict[str, str] | None = None,
    position_aliases: dict[str, str] | None = None,
) -> tuple[list[Row], list[dict[str, Any]], int]:
    cleaned: list[Row] = []
    issues = []
    seen = set()
    duplicates = 0
    for index, raw in enumerate(rows, start=2):
        try:
            row = normalize_record(
                raw, kind, club_aliases=club_aliases, position_aliases=position_aliases
            )
        except (ValueError, TypeError, OverflowError) as error:
            issues.append(
                {"source": kind, "csv_row": index, "reason": "invalid_row", "detail": str(error)}
            )
            continue
        fingerprint = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if fingerprint in seen:
            duplicates += 1
            continue
        seen.add(fingerprint)
        cleaned.append(row)
    return cleaned, issues, duplicates


def build_dataset(
    statistics: list[Row],
    valuations: list[Row],
    *,
    policies: dict[str, ValuationPolicy],
    mapping: IdMapping | None = None,
    club_aliases: dict[str, str] | None = None,
    position_aliases: dict[str, str] | None = None,
) -> BuildResult:
    """Pure builder. Unknown timing policies are configuration errors, never inferred."""
    if not policies or any(normalize_season(season) != season for season in policies):
        raise ValueError("Supply explicit policies keyed by canonical YYYY/YY seasons")
    stats, stats_issues, stats_duplicates = normalize_rows(
        statistics, "statistics", club_aliases=club_aliases, position_aliases=position_aliases
    )
    values, value_issues, value_duplicates = normalize_rows(
        valuations, "valuations", club_aliases=club_aliases
    )
    missing_policies = {str(row["season"]) for row in stats} - policies.keys()
    if missing_policies:
        raise ValueError(f"Missing valuation policies: {sorted(missing_policies)}")
    matcher = PlayerMatcher(values, mapping)
    groups: dict[tuple[str, str, str], list[Row]] = defaultdict(list)
    for row in stats:
        groups[(*identity(row), str(row["season"]))].append(row)
    issues = stats_issues + value_issues
    matched = Counter()
    output = []
    audit = []
    # Detect distinct statistics IDs that resolve to one value-source player in a season.
    candidates: dict[tuple[str, str, str], list[tuple[Row, dict[str, Any]]]] = defaultdict(list)
    for key, group in sorted(groups.items()):
        row = group[0]
        context = {"source": "statistics", "player_id": f"{key[0]}:{key[1]}", "season": key[2]}
        if len(group) > 1:
            issues.append(
                dict(context, reason="conflicting_player_season", rejected_rows=len(group))
            )
            continue
        policy = policies[str(row["season"])]
        if str(row["statistics_as_of"]) > policy.statistics_cutoff:
            issues.append(dict(context, reason="statistics_after_cutoff"))
            continue
        match = matcher.match(row)
        if match.issue:
            issues.append(dict(context, reason=match.issue))
            continue
        value, issue = select_valuation(match.records, policy)
        if issue:
            issues.append(dict(context, reason=issue))
            continue
        assert value is not None
        record = dict(
            row,
            player_id=context["player_id"],
            market_value_eur=value["market_value_eur"],
            market_value_date=value["market_value_date"],
        )
        record = add_per_90(record)
        trace = dict(
            context,
            match_method=match.method,
            valuation_namespace=value["id_namespace"],
            valuation_player_id=value["player_id"],
            statistics_as_of=row["statistics_as_of"],
            market_value_date=value["market_value_date"],
        )
        candidates[(*identity(value), str(row["season"]))].append((record, trace))
    for group in candidates.values():
        if len(group) > 1:
            for _, trace in group:
                issues.append(dict(trace, reason="many_to_one_identity"))
            continue
        record, trace = group[0]
        output.append({column: record.get(column) for column in OUTPUT_COLUMNS})
        audit.append(trace)
        matched[trace["match_method"]] += 1
    output.sort(key=lambda row: (str(row["season"]), str(row["player_id"])))
    report = {
        "input_rows": {"statistics": len(statistics), "valuations": len(valuations)},
        "duplicates_removed": {"statistics": stats_duplicates, "valuations": value_duplicates},
        "final_rows": len(output),
        "rejected_statistics_rows": len(statistics) - stats_duplicates - len(output),
        "zero_minute_rows": sum(row["minutes"] == 0 for row in output),
        "missing_values": {
            column: sum(row[column] is None for row in output) for column in OUTPUT_COLUMNS
        },
        "match_methods": dict(matched),
        "issues": issues,
        "matches": audit,
        "valuation_policies": {
            season: asdict(policy) for season, policy in sorted(policies.items())
        },
    }
    return BuildResult(output, report)


def write_dataset(result: BuildResult, output_dir: Path) -> None:
    """Write only a nonempty result; refuse to overwrite existing pipeline outputs."""
    if not result.rows:
        raise ValueError("No accepted rows; inspect the report before producing a dataset")
    seen = set()
    for row in result.rows:
        if set(row) != set(OUTPUT_COLUMNS):
            raise ValueError("Merged row does not match the dataset schema")
        key = (row["player_id"], row["season"])
        if not row["player_id"] or key in seen:
            raise ValueError("Duplicate or missing player-season identity")
        seen.add(key)
        normalize_season(row["season"])
        iso_date(row["market_value_date"])
        number(row["market_value_eur"], required=True)
        number(row["minutes"], required=True)
        expected = add_per_90(row)
        if any(row[column] != expected[column] for column in DERIVED_COLUMNS):
            raise ValueError("Merged per-90 features do not match the statistics")
    if result.report.get("final_rows") != len(result.rows):
        raise ValueError("Cleaning report row count does not match dataset")
    # Check JSON serialization before creating either output file.
    report_json = json.dumps(result.report, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    dataset_path = output_dir / "player_seasons.csv"
    report_path = output_dir / "cleaning_report.json"
    if dataset_path.exists() or report_path.exists():
        raise FileExistsError("Output already exists; select a new output directory for this run")
    output_dir.mkdir(parents=True, exist_ok=True)
    with dataset_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(result.rows)
    with report_path.open("x", encoding="utf-8") as stream:
        stream.write(report_json)
