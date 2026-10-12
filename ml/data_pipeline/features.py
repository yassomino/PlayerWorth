"""Per-90 helpers shared by dataset preparation and later ML work."""

from .normalization import Row, number

PER_90_STATS = ("goals", "assists", "shots", "key_passes", "tackles", "interceptions")
DERIVED_COLUMNS = tuple(f"{stat}_per_90" for stat in PER_90_STATS) + ("goal_contributions_per_90",)


def per_90(stat: float | None, minutes: float | None) -> float | None:
    """Return missing for zero/missing minutes or a missing count, never infinity."""
    numerator = number(stat)
    denominator = number(minutes)
    if numerator is None or denominator is None or denominator == 0:
        return None
    return number(numerator / denominator * 90)


def add_per_90(row: Row) -> Row:
    result = dict(row)
    minutes = number(row.get("minutes"))
    for stat in PER_90_STATS:
        result[f"{stat}_per_90"] = per_90(number(row.get(stat)), minutes)
    goals, assists = number(row.get("goals")), number(row.get("assists"))
    contributions = None if goals is None or assists is None else goals + assists
    result["goal_contributions_per_90"] = per_90(contributions, minutes)
    return result
