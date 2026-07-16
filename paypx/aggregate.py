"""League-level aggregation: mean pay index by position, with variance flags.

Given per-player rows (from build), aggregate the index by position across all
clubs in a league, at both broad and granular levels. Flag positions whose
spread across clubs is wide enough that the mean may hide a split (the brief's
CB/FB observation).
"""

from __future__ import annotations

import pandas as pd

# Coefficient-of-variation threshold above which a position's mean is flagged
# as "high spread — inspect the per-club distribution".
HIGH_SPREAD_CV = 0.35


def rows_to_frame(all_rows: list[dict]) -> pd.DataFrame:
    """Build a tidy DataFrame from build.PlayerRow dicts, matched-only."""
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
    df = df[df["matched"] & df["index"].notna()].copy()
    return df


def aggregate(df: pd.DataFrame, level: str) -> pd.DataFrame:
    """Aggregate index by position for a league.

    ``level`` is "broad" or "granular". Returns one row per (league, position)
    with mean/median index, spread stats, sample size and a high-spread flag.
    """
    col = "broad" if level == "broad" else "granular"
    if df.empty or col not in df:
        return pd.DataFrame()
    g = df.groupby(["league", col])["index"]
    out = g.agg(
        mean_index="mean",
        median_index="median",
        std_index="std",
        min_index="min",
        max_index="max",
        n_players="count",
    ).reset_index().rename(columns={col: "position"})
    out["std_index"] = out["std_index"].fillna(0.0)
    out["cv"] = (out["std_index"] / out["mean_index"]).where(
        out["mean_index"] != 0, 0.0
    )
    out["high_spread"] = out["cv"] >= HIGH_SPREAD_CV
    out["level"] = level
    for c in ["mean_index", "median_index", "std_index", "min_index",
              "max_index", "cv"]:
        out[c] = out[c].round(3)
    return out.sort_values(["league", "position"]).reset_index(drop=True)


def league_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return {'broad': df, 'granular': df} index tables."""
    return {
        "broad": aggregate(df, "broad"),
        "granular": aggregate(df, "granular"),
    }


def sanity_check(df: pd.DataFrame, clubs: list[str]) -> pd.DataFrame:
    """Per-club, per-position mean index for the named sanity-check clubs."""
    sub = df[df["club"].isin(clubs)]
    if sub.empty:
        return pd.DataFrame()
    out = (
        sub.groupby(["club", "granular"])["index"]
        .mean().round(3).reset_index()
        .pivot(index="club", columns="granular", values="index")
    )
    return out
