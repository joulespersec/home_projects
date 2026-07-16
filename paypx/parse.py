"""Parse cached HTML into structured wage and lineup records.

Parsers are written defensively: sources change their markup, so each parser
tries a specific known structure first and falls back to a generic
"table with a name column + a money/minutes column" heuristic. Money strings
are normalised to integer annual base salary.

Record shapes (plain dicts, JSON-serialisable):

  wage record   : {"name", "weekly", "annual", "currency"}
  lineup record : {"name", "pos_raw", "granular", "minutes", "starts"}
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from . import positions

_CURRENCY = {"£": "GBP", "€": "EUR", "$": "USD"}
_MULT = {"k": 1_000, "m": 1_000_000, "bn": 1_000_000_000, "b": 1_000_000_000}


def parse_money(text: str) -> tuple[int | None, str | None]:
    """Parse a money string to (amount:int, currency:str|None).

    Handles '£325,000', '€27.3m', '$180K', '19.5 M', plain '250000'.
    Returns (None, currency) when no number is found.
    """
    if text is None:
        return None, None
    s = str(text).strip()
    currency = None
    for sym, code in _CURRENCY.items():
        if sym in s:
            currency = code
            break
    if currency is None:
        m = re.search(r"\b(GBP|EUR|USD)\b", s, re.I)
        if m:
            currency = m.group(1).upper()
    m = re.search(r"([\d][\d,\.\s]*)\s*(bn|b|m|k)?", s, re.I)
    if not m:
        return None, currency
    num = m.group(1).replace(",", "").replace(" ", "")
    try:
        val = float(num)
    except ValueError:
        return None, currency
    suffix = (m.group(2) or "").lower()
    if suffix in _MULT:
        val *= _MULT[suffix]
    return int(round(val)), currency


# --- Wages (salaryleaks) ---------------------------------------------------

def parse_salaryleaks(html: str) -> list[dict]:
    """Parse a salaryleaks club page into wage records.

    Expected columns include a player name plus weekly and/or annual/yearly
    gross base wage. We take fixed base salary (the table's headline wage),
    ignoring any bonus/image-rights columns.
    """
    soup = BeautifulSoup(html, "lxml")
    records: list[dict] = []
    for table in soup.find_all("table"):
        headers = [
            th.get_text(strip=True).lower()
            for th in table.find_all("th")
        ]
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [c.get_text(strip=True).lower()
                           for c in first_row.find_all(["td", "th"])]
        name_col = _find_col(headers, ["player", "name"])
        weekly_col = _find_col(headers, ["weekly", "week", "per week", "p/w"])
        annual_col = _find_col(
            headers, ["annual", "yearly", "per year", "year", "gross"]
        )
        if name_col is None or (weekly_col is None and annual_col is None):
            continue
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) <= name_col:
                continue
            name = cells[name_col].get_text(strip=True)
            if not name or name.lower() in ("player", "name"):
                continue
            weekly = annual = None
            currency = None
            if weekly_col is not None and len(cells) > weekly_col:
                weekly, currency = parse_money(cells[weekly_col].get_text())
            if annual_col is not None and len(cells) > annual_col:
                annual, cur2 = parse_money(cells[annual_col].get_text())
                currency = currency or cur2
            if weekly and not annual:
                annual = weekly * 52
            if annual and not weekly:
                weekly = int(round(annual / 52))
            if not annual:
                continue
            records.append({
                "name": name,
                "weekly": weekly,
                "annual": annual,
                "currency": currency or "GBP",
            })
        if records:
            break  # first table that yielded rows is the wage table
    return records


# --- Lineups (fbref squad standard stats) ----------------------------------

def parse_fbref_squad(html: str) -> list[dict]:
    """Parse fbref squad 'Standard Stats' into lineup records.

    fbref wraps some tables in HTML comments; we un-comment before parsing.
    We read Player, Pos, Min (minutes) and starts where available. Granular
    position is resolved from the Pos code via the taxonomy (fbref Pos is
    coarse — DF/MF/FW — so many players resolve to CB/CM/ST and need a
    granular override; see build.load_club for how overrides are applied).
    """
    html = html.replace("<!--", "").replace("-->", "")
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id=re.compile(r"stats_standard"))
    if table is None:
        # fall back to first table with a 'Player' + 'Min' header
        for t in soup.find_all("table"):
            hs = [th.get_text(strip=True).lower() for th in t.find_all("th")]
            if "player" in hs and any("min" == h or "minutes" in h for h in hs):
                table = t
                break
    if table is None:
        return []

    records: list[dict] = []
    body = table.find("tbody") or table
    for tr in body.find_all("tr"):
        if "thead" in (tr.get("class") or []):
            continue
        cell = {}
        for c in tr.find_all(["td", "th"]):
            stat = c.get("data-stat")
            if stat:
                cell[stat] = c.get_text(strip=True)
        name = cell.get("player") or cell.get("player_name")
        if not name or name.lower() == "player":
            continue
        pos_raw = cell.get("position", "")
        minutes = _to_int(cell.get("minutes"))
        starts = _to_int(cell.get("games_starts"))
        records.append({
            "name": name,
            "pos_raw": pos_raw,
            "granular": positions.to_granular(pos_raw),
            "minutes": minutes or 0,
            "starts": starts or 0,
        })
    return records


# --- helpers ---------------------------------------------------------------

def _find_col(headers: list[str], keys: list[str]) -> int | None:
    for i, h in enumerate(headers):
        for k in keys:
            if k in h:
                return i
    return None


def _to_int(text) -> int | None:
    if text is None:
        return None
    s = re.sub(r"[^\d]", "", str(text))
    return int(s) if s else None
