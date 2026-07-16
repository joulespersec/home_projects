"""Position taxonomy and the conventions that resolve the brief's edge cases.

Two levels are used throughout the pipeline:

    broad    : GK, DEF, MID, FWD
    granular : GK, CB, FB, DM, CM, AM, W, ST

Convention decisions (applied consistently everywhere — see README):

  * Wingers are their own granular bucket ``W`` and roll up to broad ``FWD``
    (they are attackers, not midfielders). This is the single most common
    cross-source disagreement; we always treat a wide attacker as ``W``.
  * Attacking midfielders are ``AM`` and roll up to broad ``MID``. A player who
    plays "in the hole" / as a 10 is ``AM``; a player who starts wide and hugs
    the touchline is ``W``, even if nominally a "forward".
  * Full-backs and wing-backs collapse into ``FB`` (broad ``DEF``).
  * Holding / defensive mids are ``DM``; box-to-box and deep playmakers are
    ``CM``; both roll up to broad ``MID``.
  * Centre-forwards / strikers / lone 9s are ``ST`` (broad ``FWD``).

The granular set intentionally has no separate "CDM vs CM vs CAM" beyond
DM/CM/AM, matching the manual sanity-check taxonomy in the brief.
"""

from __future__ import annotations

# Canonical granular codes, in a sensible pitch order (back to front).
GRANULAR = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"]

# Canonical broad codes.
BROAD = ["GK", "DEF", "MID", "FWD"]

# granular -> broad rollup.
GRANULAR_TO_BROAD = {
    "GK": "GK",
    "CB": "DEF",
    "FB": "DEF",
    "DM": "MID",
    "CM": "MID",
    "AM": "MID",
    "W": "FWD",
    "ST": "FWD",
}

# Aliases seen across sources (fbref codes, transfermarkt slot names,
# transfermarkt/Capology role labels, common abbreviations) -> granular code.
# Keys are compared case-insensitively after stripping punctuation/whitespace.
_ALIAS = {
    # Goalkeeper
    "gk": "GK", "goalkeeper": "GK", "keeper": "GK", "tw": "GK",
    # Centre-back
    "cb": "CB", "centreback": "CB", "centerback": "CB", "centraldefender": "CB",
    "iv": "CB", "df": "CB", "defender": "CB", "sw": "CB", "sweeper": "CB",
    "d(c)": "CB", "dc": "CB",
    # Full-back / wing-back
    "fb": "FB", "rb": "FB", "lb": "FB", "rwb": "FB", "lwb": "FB",
    "fullback": "FB", "wingback": "FB", "rightback": "FB", "leftback": "FB",
    "d(r)": "FB", "d(l)": "FB", "rv": "FB", "lv": "FB",
    # Defensive / holding mid
    "dm": "DM", "cdm": "DM", "defensivemidfield": "DM", "holdingmidfield": "DM",
    "dmf": "DM", "m(cd)": "DM",
    # Central mid
    "cm": "CM", "mf": "CM", "midfielder": "CM", "centralmidfield": "CM",
    "boxtobox": "CM", "mc": "CM", "m(c)": "CM", "zm": "CM",
    # Attacking mid
    "am": "AM", "cam": "AM", "attackingmidfield": "AM", "playmaker": "AM",
    "amf": "AM", "secondstriker": "AM", "ss": "AM", "m(ca)": "AM", "os": "AM",
    "10": "AM",
    # Winger / wide attacker
    "w": "W", "rw": "W", "lw": "W", "winger": "W", "wideattacker": "W",
    "rightwinger": "W", "leftwinger": "W", "rm": "W", "lm": "W",
    "rightmidfield": "W", "leftmidfield": "W", "am(r)": "W", "am(l)": "W",
    "ra": "W", "la": "W", "wideforward": "W",
    # Striker / centre-forward
    "st": "ST", "cf": "ST", "fw": "ST", "striker": "ST", "centreforward": "ST",
    "centerforward": "ST", "forward": "ST", "lonestriker": "ST", "s": "ST",
    "st(c)": "ST", "hs": "ST",
}


def _key(raw: str) -> str:
    return "".join(ch for ch in raw.lower() if ch.isalnum())


def to_granular(raw: str) -> str | None:
    """Map an arbitrary source position label to a canonical granular code.

    Returns ``None`` when the label cannot be resolved (caller should flag the
    player for manual position review rather than silently guessing).

    Compound labels (e.g. ``"DF,MF"`` from fbref, ``"CB/RB"``) resolve to the
    *first* recognised token, which fbref orders by primary position.
    """
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if text.upper() in GRANULAR:
        return text.upper()
    # Try the whole string first, then split on common separators.
    candidates = [text]
    for sep in (",", "/", "-", ";", "|", " "):
        if sep in text:
            candidates = [p for p in text.split(sep) if p.strip()]
            break
    for cand in candidates:
        code = _ALIAS.get(_key(cand))
        if code:
            return code
    return None


def to_broad(granular_or_raw: str) -> str | None:
    """Map a granular code (or raw label) to a broad code."""
    if granular_or_raw in GRANULAR_TO_BROAD:
        return GRANULAR_TO_BROAD[granular_or_raw]
    g = to_granular(granular_or_raw)
    return GRANULAR_TO_BROAD.get(g) if g else None


# Standard forced formation for the robustness check: 4-3-3 expressed in
# granular slots. Used to force every club into a comparable XI shape.
FORCED_433 = ["GK", "CB", "CB", "FB", "FB", "DM", "CM", "CM", "W", "W", "ST"]
