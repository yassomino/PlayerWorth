"""Serializable position normalization for the experimental pipeline."""

import pandas as pd

POSITIONS = ("AM", "CB", "CM", "DM", "FB", "GK", "ST", "W", "UNKNOWN")


def normalize_position(values: pd.DataFrame) -> pd.DataFrame:
    """Preserve cohort; only known broad categories enter the encoder."""
    result = values.copy()
    result["position"] = result["position"].astype("string").str.strip().str.upper()
    result["position"] = result["position"].where(result["position"].isin(POSITIONS), "UNKNOWN")
    return result
