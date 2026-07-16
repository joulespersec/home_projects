"""Merge wages + lineup per club, select the XI, compute the pay index.

A club's canonical inputs are two source lists (wages, lineup). They come from
either the shipped seed JSON (verified 5 clubs) or the scrape+parse path. This
module joins them by name, selects the starting XI two ways (actual most-used
and forced 4-3-3), then computes index = salary / team-median (median = 1.00).
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, asdict

from . import config, parse, positions, scrape
from .names import match_names


@dataclass
class PlayerRow:
    club: str
    league: str
    season: str
    name: str
    granular: str | None
    broad: str | None
    annual: int
    weekly: int | None
    currency: str
    minutes: int
    starts: int
    index: float | None = None       # salary / team median (filled later)
    formation_mode: str = "actual"   # "actual" | "forced433"
    matched: bool = True             # False => wage/lineup join failed


@dataclass
class ClubResult:
    club: str
    league: str
    season: str
    formation: str                   # e.g. "actual" or "forced433"
    median: float
    rows: list[PlayerRow]
    unmatched_lineup: list[str]      # in XI but no wage found
    unmatched_wage: list[str]        # had a wage but not in XI/lineup


# --- Loading a club's two source lists -------------------------------------

def load_club(club: config.Club, season: str) -> dict:
    """Return {"wages": [...], "lineup": [...], "currency": str} for a club.

    Prefers shipped seed JSON (``data/seed/{club}.json``). Otherwise reads the
    cached raw HTML and parses it. Raises if neither is available (never
    fabricates).
    """
    seed_path = config.SEED / f"{club.key}.json"
    if seed_path.exists():
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        return {
            "wages": data["wages"],
            "lineup": data["lineup"],
            "currency": data.get("currency", "GBP"),
            "provenance": data.get("provenance", "seed"),
        }

    # Scrape path (requires network + reachable sources).
    wage_html = scrape.fetch(scrape.wage_url(club), config.WAGE_SOURCE, club.key)
    lineup_html = scrape.fetch(
        scrape.fbref_url(club), config.LINEUP_SOURCE, club.key
    )
    wages = parse.parse_salaryleaks(wage_html)
    lineup = parse.parse_fbref_squad(lineup_html)
    if not wages or not lineup:
        raise RuntimeError(
            f"parsed empty data for {club.key} "
            f"(wages={len(wages)}, lineup={len(lineup)})"
        )
    currency = wages[0].get("currency", "GBP") if wages else "GBP"
    return {"wages": wages, "lineup": lineup, "currency": currency,
            "provenance": "scrape"}


# --- XI selection ----------------------------------------------------------

def _most_used_xi(lineup: list[dict]) -> list[dict]:
    """Top 11 lineup players by minutes (tie-break: starts)."""
    ranked = sorted(
        lineup, key=lambda r: (r.get("minutes", 0), r.get("starts", 0)),
        reverse=True,
    )
    return ranked[:11]


# Fallback order for forced 4-3-3 when a bucket is short: which other granular
# buckets can cover a needed slot (nearest role first).
_FORCED_FALLBACK = {
    "GK": ["GK"],
    "CB": ["CB", "FB", "DM"],
    "FB": ["FB", "CB", "W"],
    "DM": ["DM", "CM", "CB"],
    "CM": ["CM", "DM", "AM"],
    "W": ["W", "AM", "ST", "FB"],
    "ST": ["ST", "W", "AM"],
}


def _forced_433_xi(lineup: list[dict]) -> list[dict]:
    """Force a 4-3-3 (GK, CB, CB, FB, FB, DM, CM, CM, W, W, ST).

    Fills each slot with the highest-minutes available player from the slot's
    granular bucket, backfilling from nearest roles when a bucket runs short.
    Robustness check only: it reclassifies some players into unfamiliar slots.
    """
    pool = sorted(lineup, key=lambda r: (r.get("minutes", 0),
                                         r.get("starts", 0)), reverse=True)
    used: set[int] = set()
    picked: list[dict] = []
    for slot in positions.FORCED_433:
        chosen = None
        for bucket in _FORCED_FALLBACK[slot]:
            for i, r in enumerate(pool):
                if i in used:
                    continue
                if r.get("granular") == bucket:
                    chosen = i
                    break
            if chosen is not None:
                break
        if chosen is None:  # nothing left that fits — take best remaining
            for i, r in enumerate(pool):
                if i not in used:
                    chosen = i
                    break
        if chosen is not None:
            used.add(chosen)
            row = dict(pool[chosen])
            row["forced_slot"] = slot  # record the slot it was forced into
            picked.append(row)
    return picked


# --- Merge + compute -------------------------------------------------------

def build_club(club: config.Club, season: str,
               formation: str = "actual") -> ClubResult:
    """Build one club's XI result with per-player pay index.

    ``formation`` is "actual" (most-used XI) or "forced433".
    """
    src = load_club(club, season)
    wages, lineup, currency = src["wages"], src["lineup"], src["currency"]

    if formation == "forced433":
        xi = _forced_433_xi(lineup)
        pos_key = "forced_slot"
    else:
        xi = _most_used_xi(lineup)
        pos_key = "granular"

    # Join XI names -> wage names.
    lineup_names = [p["name"] for p in xi]
    wage_names = [w["name"] for w in wages]
    m = match_names(lineup_names, wage_names)
    wage_by_name = {w["name"]: w for w in wages}

    rows: list[PlayerRow] = []
    for p in xi:
        wage_name = m.pairs.get(p["name"])
        wage = wage_by_name.get(wage_name) if wage_name else None
        granular = p.get(pos_key) or p.get("granular")
        annual = wage["annual"] if wage else None
        rows.append(PlayerRow(
            club=club.key, league=club.league, season=season, name=p["name"],
            granular=granular, broad=positions.GRANULAR_TO_BROAD.get(granular),
            annual=annual if annual else 0,
            weekly=wage.get("weekly") if wage else None,
            currency=currency, minutes=p.get("minutes", 0),
            starts=p.get("starts", 0),
            formation_mode=formation, matched=wage is not None,
        ))

    # Median over matched players only (index needs a salary).
    salaries = [r.annual for r in rows if r.matched and r.annual > 0]
    median = statistics.median(salaries) if salaries else 0.0
    for r in rows:
        if r.matched and r.annual > 0 and median > 0:
            r.index = round(r.annual / median, 4)

    return ClubResult(
        club=club.key, league=club.league, season=season, formation=formation,
        median=median, rows=rows,
        unmatched_lineup=m.unmatched_lineup,
        unmatched_wage=m.unmatched_wage,
    )


def rows_to_records(result: ClubResult) -> list[dict]:
    return [asdict(r) for r in result.rows]
