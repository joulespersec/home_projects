"""Project configuration: paths, leagues, clubs, season defaults.

The club registry maps a canonical club key to the per-source slugs the
scrapers need. Slugs are best-effort defaults; the scraper reads them from
here so a single edit fixes a moved/renamed source page without touching code.

Only the five sanity-check clubs have verified seed data shipped in the repo
(``data/seed``). The remaining clubs are registered so a networked run can
scrape all 20 per league; their slugs should be confirmed on first live run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --- Paths -----------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"           # cached raw HTML/JSON per club per source
SEED = DATA / "seed"         # curated, verified data for the 5 sanity clubs
INTERIM = DATA / "interim"   # merged per-club tables (parquet/csv)
OUTPUT = DATA / "output"     # index tables + charts
CHARTS = OUTPUT / "charts"

for _p in (RAW, SEED, INTERIM, OUTPUT, CHARTS):
    _p.mkdir(parents=True, exist_ok=True)

# --- Season ----------------------------------------------------------------

# Default season: most recent COMPLETE season (has full minutes/lineup data).
# The brief scopes 2026-27, but as of build time that season is unplayed, so
# there is no "most-used XI" to compute. Override with --season on the CLI.
DEFAULT_SEASON = "2025-26"

# --- Sources ---------------------------------------------------------------

WAGE_SOURCE = "salaryleaks"          # readable HTML wage tables
LINEUP_SOURCE = "fbref"              # squad minutes-by-position; top-11 = XI
# transfermarkt is supported as an alternative lineup source (explicit
# most-used-formation graphic); select with --lineup-source transfermarkt.

SALARYLEAKS_BASE = "https://salaryleaks.com/football/teams"
FBREF_BASE = "https://fbref.com/en/squads"
TRANSFERMARKT_BASE = "https://www.transfermarkt.com"

# Polite scraping defaults (respect the sources; avoid re-fetch via cache).
REQUEST_HEADERS = {
    "User-Agent": os.environ.get(
        "PAYPX_USER_AGENT",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
REQUEST_DELAY_SECONDS = float(os.environ.get("PAYPX_DELAY", "3.0"))
REQUEST_TIMEOUT = 30


@dataclass
class Club:
    key: str                 # canonical short key, e.g. "man-city"
    name: str                # display name
    league: str              # league key, e.g. "epl"
    salaryleaks_slug: str    # slug on salaryleaks.com
    fbref_id: str = ""       # fbref squad id (8-char hash) when known
    fbref_slug: str = ""     # fbref squad slug, e.g. "Manchester-City-Stats"
    transfermarkt_slug: str = ""
    transfermarkt_id: str = ""


@dataclass
class League:
    key: str
    name: str
    country: str
    clubs: list[Club] = field(default_factory=list)


# --- Club registry ---------------------------------------------------------
# Verified seed clubs carry their fbref ids; the rest need confirmation on the
# first networked run (slugs follow each source's usual pattern).

_EPL = [
    Club("man-city", "Manchester City", "epl", "manchester-city",
         "b8fd03ef", "Manchester-City-Stats"),
    Club("liverpool", "Liverpool", "epl", "liverpool",
         "822bd0ba", "Liverpool-Stats"),
    Club("arsenal", "Arsenal", "epl", "arsenal",
         "18bb7c10", "Arsenal-Stats"),
    Club("chelsea", "Chelsea", "epl", "chelsea", "cff3d9bb", "Chelsea-Stats"),
    Club("man-united", "Manchester United", "epl", "manchester-united",
         "19538871", "Manchester-United-Stats"),
    Club("tottenham", "Tottenham Hotspur", "epl", "tottenham-hotspur",
         "361ca564", "Tottenham-Hotspur-Stats"),
    Club("newcastle", "Newcastle United", "epl", "newcastle-united",
         "b2b47a98", "Newcastle-United-Stats"),
    Club("aston-villa", "Aston Villa", "epl", "aston-villa",
         "8602292d", "Aston-Villa-Stats"),
    Club("brighton", "Brighton & Hove Albion", "epl", "brighton-hove-albion",
         "d07537b9", "Brighton-and-Hove-Albion-Stats"),
    Club("west-ham", "West Ham United", "epl", "west-ham-united",
         "7c21e445", "West-Ham-United-Stats"),
    Club("crystal-palace", "Crystal Palace", "epl", "crystal-palace",
         "47c64c55", "Crystal-Palace-Stats"),
    Club("everton", "Everton", "epl", "everton", "d3fd31cc", "Everton-Stats"),
    Club("fulham", "Fulham", "epl", "fulham", "fd962109", "Fulham-Stats"),
    Club("brentford", "Brentford", "epl", "brentford",
         "cd051869", "Brentford-Stats"),
    Club("nottingham-forest", "Nottingham Forest", "epl", "nottingham-forest",
         "e4a775cb", "Nottingham-Forest-Stats"),
    Club("wolves", "Wolverhampton Wanderers", "epl", "wolverhampton-wanderers",
         "8cec06e1", "Wolverhampton-Wanderers-Stats"),
    Club("bournemouth", "AFC Bournemouth", "epl", "bournemouth",
         "4ba7cbea", "Bournemouth-Stats"),
    Club("burnley", "Burnley", "epl", "burnley", "943e8050", "Burnley-Stats"),
    Club("leeds", "Leeds United", "epl", "leeds-united",
         "5bfb9659", "Leeds-United-Stats"),
    Club("sunderland", "Sunderland", "epl", "sunderland",
         "8ef52968", "Sunderland-Stats"),
]

_LALIGA = [
    Club("real-madrid", "Real Madrid", "laliga", "real-madrid",
         "53a2f082", "Real-Madrid-Stats"),
    Club("barcelona", "Barcelona", "laliga", "barcelona",
         "206d90db", "Barcelona-Stats"),
    Club("atletico-madrid", "Atletico Madrid", "laliga", "atletico-madrid",
         "db3b9613", "Atletico-Madrid-Stats"),
    Club("athletic-club", "Athletic Club", "laliga", "athletic-bilbao",
         "2b390eca", "Athletic-Club-Stats"),
    Club("real-sociedad", "Real Sociedad", "laliga", "real-sociedad",
         "e31d1cd9", "Real-Sociedad-Stats"),
    Club("real-betis", "Real Betis", "laliga", "real-betis",
         "fc536746", "Real-Betis-Stats"),
    Club("villarreal", "Villarreal", "laliga", "villarreal",
         "2a8183b3", "Villarreal-Stats"),
    Club("valencia", "Valencia", "laliga", "valencia",
         "dcc91a7b", "Valencia-Stats"),
    Club("sevilla", "Sevilla", "laliga", "sevilla", "ad2be733", "Sevilla-Stats"),
    Club("girona", "Girona", "laliga", "girona", "9024a00a", "Girona-Stats"),
    Club("celta-vigo", "Celta Vigo", "laliga", "celta-vigo",
         "f25da7fb", "Celta-Vigo-Stats"),
    Club("rayo-vallecano", "Rayo Vallecano", "laliga", "rayo-vallecano",
         "98e8af82", "Rayo-Vallecano-Stats"),
    Club("osasuna", "Osasuna", "laliga", "osasuna", "03c57e2b", "Osasuna-Stats"),
    Club("mallorca", "Mallorca", "laliga", "mallorca",
         "2aa12281", "Mallorca-Stats"),
    Club("getafe", "Getafe", "laliga", "getafe", "7848767a", "Getafe-Stats"),
    Club("espanyol", "Espanyol", "laliga", "espanyol",
         "a8661628", "Espanyol-Stats"),
    Club("alaves", "Alaves", "laliga", "deportivo-alaves",
         "8d6fd021", "Alaves-Stats"),
    Club("elche", "Elche", "laliga", "elche", "6c8b07df", "Elche-Stats"),
    Club("levante", "Levante", "laliga", "levante", "9800b6a1", "Levante-Stats"),
    Club("real-oviedo", "Real Oviedo", "laliga", "real-oviedo",
         "readba2f", "Real-Oviedo-Stats"),
]

LEAGUES: dict[str, League] = {
    "epl": League("epl", "Premier League", "England", _EPL),
    "laliga": League("laliga", "La Liga", "Spain", _LALIGA),
}

# Clubs with shipped, verified seed data (used for the sanity check).
SEED_CLUBS = ["man-city", "liverpool", "arsenal", "real-madrid", "barcelona"]


def get_league(key: str) -> League:
    if key not in LEAGUES:
        raise KeyError(f"Unknown league {key!r}; known: {sorted(LEAGUES)}")
    return LEAGUES[key]


def get_club(key: str) -> Club:
    for lg in LEAGUES.values():
        for c in lg.clubs:
            if c.key == key:
                return c
    raise KeyError(f"Unknown club {key!r}")


def all_clubs() -> list[Club]:
    return [c for lg in LEAGUES.values() for c in lg.clubs]
