"""Conservative normalization of canonical source records."""

import math
import re
import unicodedata
from datetime import date
from typing import TypeAlias

Cell: TypeAlias = str | int | float | None
Row: TypeAlias = dict[str, Cell]
POSITIONS = frozenset({"GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"})
COUNTS = (
    "appearances",
    "starts",
    "minutes",
    "goals",
    "assists",
    "shots",
    "shots_on_target",
    "key_passes",
    "passes",
    "dribbles",
    "tackles",
    "interceptions",
    "yellow_cards",
    "red_cards",
)


def text(value: Cell) -> str:
    """Collapse whitespace without discarding accents or changing display names."""
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def normalize_name(value: Cell) -> str:
    """Create an exact comparison key, not a unique player identifier."""
    return text(value).casefold()


def normalize_club(value: Cell, aliases: dict[str, str] | None = None) -> str:
    """Apply only supplied, reviewed aliases; never guess club equivalence."""
    key = normalize_name(value)
    lookup = {normalize_name(k): normalize_name(v) for k, v in (aliases or {}).items()}
    if any(not source or not target for source, target in lookup.items()):
        raise ValueError("Club aliases cannot contain empty names")
    if any(lookup.get(target, target) != target for target in lookup.values()):
        raise ValueError("Club aliases must point directly to stable canonical names")
    return lookup.get(key, key)


def normalize_position(value: Cell, aliases: dict[str, str] | None = None) -> str | None:
    if not text(value):
        return None
    key = text(value).upper()
    lookup = {text(k).upper(): text(v).upper() for k, v in (aliases or {}).items()}
    if any(source in POSITIONS and target != source for source, target in lookup.items()):
        raise ValueError("Position aliases cannot redefine canonical positions")
    position = lookup.get(key, key)
    if position not in POSITIONS:
        raise ValueError(f"Unmapped position: {value!r}; supply a reviewed position alias")
    return position


def normalize_season(value: Cell) -> str:
    match = re.fullmatch(r"(\d{4})[/-](\d{2}|\d{4})", text(value))
    if not match:
        raise ValueError(f"Invalid season: {value!r}")
    start, end = match.groups()
    expected = str(int(start) + 1)
    if end != (expected[-2:] if len(end) == 2 else expected):
        raise ValueError(f"Nonconsecutive season: {value!r}")
    return f"{start}/{expected[-2:]}"


def iso_date(value: Cell) -> str:
    raw = text(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        raise ValueError(f"Expected ISO date YYYY-MM-DD: {value!r}")
    return date.fromisoformat(raw).isoformat()


def number(value: Cell, *, required: bool = False, integer: bool = False) -> float | int | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValueError("Required numeric value is missing")
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric statistic")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"Expected a finite nonnegative number: {value!r}")
    if integer:
        if not result.is_integer():
            raise ValueError(f"Expected an integer count: {value!r}")
        return int(result)
    return result


def normalize_record(
    raw: Row,
    kind: str,
    *,
    club_aliases: dict[str, str] | None = None,
    position_aliases: dict[str, str] | None = None,
) -> Row:
    """Validate a canonical adapter row; do not impute absent statistics."""
    if kind not in {"statistics", "valuations"}:
        raise ValueError("kind must be statistics or valuations")
    row: Row = {key: text(raw.get(key)) for key in ("id_namespace", "player_id", "player_name")}
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", str(row["id_namespace"])) or not row["player_id"]:
        raise ValueError("A source ID and a nonempty ID namespace are required")
    row["name_key"] = normalize_name(row["player_name"])
    row["club"] = normalize_club(raw.get("club"), club_aliases)
    row["season"] = normalize_season(raw["season"]) if text(raw.get("season")) else None
    row["date_of_birth"] = (
        iso_date(raw["date_of_birth"]) if text(raw.get("date_of_birth")) else None
    )
    if kind == "valuations":
        if text(raw.get("currency")).upper() != "EUR":
            raise ValueError(
                "Only explicit EUR valuations are supported; currency conversion is TODO"
            )
        row["market_value_eur"] = number(raw.get("market_value_eur"), required=True)
        row["market_value_date"] = iso_date(raw.get("market_value_date"))
        row["currency"] = "EUR"
        return row
    if normalize_name(raw.get("competition")) not in {"epl", "english premier league"}:
        raise ValueError("Statistics must explicitly identify the English Premier League")
    if not all(row[key] for key in ("player_name", "club", "season")):
        raise ValueError("Statistics require player_name, club, and season")
    row["competition"] = "EPL"
    row["statistics_as_of"] = iso_date(raw.get("statistics_as_of"))
    row["position"] = normalize_position(raw.get("position"), position_aliases)
    for key in COUNTS:
        row[key] = number(raw.get(key), required=key == "minutes", integer=key != "minutes")
    row["age"] = number(raw.get("age"))
    if row["age"] is not None and not 0 < row["age"] <= 100:
        raise ValueError("Age must be greater than zero and at most 100")
    row["pass_accuracy"] = number(raw.get("pass_accuracy"))
    if row["pass_accuracy"] is not None and row["pass_accuracy"] > 100:
        raise ValueError("pass_accuracy must be a percentage in [0, 100]")
    row["club_league_position"] = number(raw.get("club_league_position"), integer=True)
    if row["club_league_position"] is not None and not 1 <= row["club_league_position"] <= 20:
        raise ValueError("club_league_position must be in [1, 20] for the initial EPL scope")
    for smaller, larger in (("starts", "appearances"), ("shots_on_target", "shots")):
        if row[smaller] is not None and row[larger] is not None and row[smaller] > row[larger]:
            raise ValueError(f"{smaller} cannot exceed {larger}")
    return row
