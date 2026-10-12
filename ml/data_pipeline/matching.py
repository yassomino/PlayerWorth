"""Resolve identities before selecting a historical valuation."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import TypeAlias

from .normalization import Row, iso_date

Identity: TypeAlias = tuple[str, str]
IdMapping: TypeAlias = dict[Identity, Identity]


def identity(row: Row) -> Identity:
    return str(row["id_namespace"]), str(row["player_id"])


@dataclass(frozen=True)
class Match:
    records: tuple[Row, ...] = ()
    method: str | None = None
    issue: str | None = None


class PlayerMatcher:
    """Exact matching only. Ambiguity stops fallback rather than guessing."""

    def __init__(self, valuations: list[Row], mapping: IdMapping | None = None) -> None:
        self.mapping = mapping or {}
        self.by_id: dict[Identity, list[Row]] = defaultdict(list)
        self.by_club_season: dict[tuple[str, ...], set[Identity]] = defaultdict(set)
        self.by_birth: dict[tuple[str, ...], set[Identity]] = defaultdict(set)
        for row in valuations:
            key = identity(row)
            self.by_id[key].append(row)
            if all(row.get(field) for field in ("name_key", "club", "season")):
                lookup = tuple(str(row[field]) for field in ("name_key", "club", "season"))
                self.by_club_season[lookup].add(key)
            if row.get("name_key") and row.get("date_of_birth"):
                self.by_birth[(str(row["name_key"]), str(row["date_of_birth"]))].add(key)

    def _resolve(self, row: Row, keys: set[Identity], method: str) -> Match:
        if len(keys) != 1:
            return Match(issue="ambiguous_identity")
        key = next(iter(keys))
        # Contradicting shared-namespace IDs are not rescued by a matching name.
        if method not in {"shared_id", "mapping"} and key[0] == identity(row)[0]:
            return Match(issue="conflicting_id")
        records = self.by_id[key]
        births = {r["date_of_birth"] for r in records if r.get("date_of_birth")}
        if len(births) > 1 or (
            row.get("date_of_birth") and births and row["date_of_birth"] not in births
        ):
            return Match(issue="conflicting_date_of_birth")
        return Match(tuple(records), method)

    def match(self, row: Row) -> Match:
        key = identity(row)
        if key in self.by_id:
            if key in self.mapping and self.mapping[key] != key:
                return Match(issue="mapping_conflicts_with_shared_id")
            return self._resolve(row, {key}, "shared_id")
        if key in self.mapping:
            target = self.mapping[key]
            if target not in self.by_id:
                return Match(issue="mapped_id_missing")
            return self._resolve(row, {target}, "mapping")
        if all(row.get(field) for field in ("name_key", "club", "season")):
            lookup = tuple(str(row[field]) for field in ("name_key", "club", "season"))
            candidates = self.by_club_season.get(lookup)
            if candidates:
                return self._resolve(row, candidates, "name_club_season")
        if row.get("name_key") and row.get("date_of_birth"):
            lookup = (str(row["name_key"]), str(row["date_of_birth"]))
            candidates = self.by_birth.get(lookup)
            if candidates:
                return self._resolve(row, candidates, "name_date_of_birth")
        return Match(issue="unmatched_identity")


@dataclass(frozen=True)
class ValuationPolicy:
    """Explicit per-season limits; there are deliberately no default dates."""

    statistics_cutoff: str
    window_start: str
    window_end: str
    next_season_start: str
    selection: str

    def __post_init__(self) -> None:
        dates = [
            date.fromisoformat(iso_date(value))
            for value in (
                self.statistics_cutoff,
                self.window_start,
                self.window_end,
                self.next_season_start,
            )
        ]
        if not dates[0] <= dates[1] <= dates[2] < dates[3]:
            raise ValueError(
                "Require statistics_cutoff <= window_start <= window_end < next_season_start"
            )
        if self.selection not in {"earliest", "latest"}:
            raise ValueError("selection must explicitly be earliest or latest")


def select_valuation(
    records: tuple[Row, ...], policy: ValuationPolicy
) -> tuple[Row | None, str | None]:
    """Select within the approved window; reject conflicting observations on a date."""
    eligible = [
        row
        for row in records
        if policy.window_start <= str(row["market_value_date"]) <= policy.window_end
    ]
    if not eligible:
        return None, "no_valuation_in_window"
    by_date: dict[str, list[Row]] = defaultdict(list)
    for row in eligible:
        by_date[str(row["market_value_date"])].append(row)
    if any(len({row["market_value_eur"] for row in group}) > 1 for group in by_date.values()):
        return None, "conflicting_valuations"
    chosen_date = (min if policy.selection == "earliest" else max)(by_date)
    # All values on this date are equal; the selected fields do not depend on order.
    return by_date[chosen_date][0], None
