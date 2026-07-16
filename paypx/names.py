"""Player-name normalisation and fuzzy matching.

The two data sources (wages vs. lineups) spell names differently: accents,
nicknames, dropped/added given names, "Jr."/suffixes, transliteration. This
module normalises a name to a comparison key and joins two lists of names,
returning matches plus the *unmatched* names on each side for manual review.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz, process

# Nickname / short-form aliases that fuzzy matching alone won't bridge.
# Map an alias (normalised) -> canonical normalised token or full name.
_NICKNAMES = {
    "leo messi": "lionel messi",
    "kun aguero": "sergio aguero",
    "dani carvajal": "daniel carvajal",
    "fede valverde": "federico valverde",
    "vini jr": "vinicius junior",
    "vinicius jr": "vinicius junior",
    "vinicius": "vinicius junior",
    "rodri": "rodrigo hernandez",
    "gabriel jesus": "gabriel jesus",
    "gabriel": "gabriel magalhaes",
    "bernardo": "bernardo silva",
    "bruno g": "bruno guimaraes",
    "trent": "trent alexander arnold",
    "taa": "trent alexander arnold",
    "big rom": "romelu lukaku",
    "dembele": "ousmane dembele",
    "ter stegen": "marc andre ter stegen",
    "lewa": "robert lewandowski",
    "pedri": "pedro gonzalez lopez",
    "gavi": "pablo martin paez gavira",
    "ferran": "ferran torres",
    "raphinha": "raphael dias belloli",
    "kdb": "kevin de bruyne",
}

# Tokens that carry no identity and should be dropped before comparison.
_SUFFIXES = {"jr", "junior", "sr", "senior", "ii", "iii", "iv"}


# Letters NFKD cannot decompose (they are distinct glyphs, not base+diacritic).
_SPECIAL = {
    "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe",
    "ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ð": "d", "Ð": "d",
    "ß": "ss", "þ": "th", "Þ": "th", "ı": "i", "ħ": "h", "ŋ": "n",
}


def strip_accents(text: str) -> str:
    """Remove diacritics: 'Håland' -> 'Haland', 'Ødegaard' -> 'Odegaard'."""
    text = "".join(_SPECIAL.get(ch, ch) for ch in text)
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def normalize(name: str) -> str:
    """Normalise a display name to a comparison key.

    Lowercase, accent-stripped, punctuation removed, suffixes dropped,
    whitespace collapsed. Nickname aliases are resolved.
    """
    if not name:
        return ""
    text = strip_accents(str(name)).lower()
    # Replace separators with spaces, drop remaining punctuation.
    text = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text)
    tokens = [t for t in text.split() if t and t not in _SUFFIXES]
    key = " ".join(tokens)
    return _NICKNAMES.get(key, key)


@dataclass
class MatchResult:
    """Outcome of joining two name lists (wages side <-> lineup side)."""

    pairs: dict[str, str]            # lineup_name -> wage_name (best match)
    scores: dict[str, float]         # lineup_name -> match score (0-100)
    unmatched_lineup: list[str]      # lineup names with no confident wage match
    unmatched_wage: list[str]        # wage names never used


def match_names(
    lineup_names: list[str],
    wage_names: list[str],
    threshold: float = 82.0,
) -> MatchResult:
    """Join lineup names to wage names by normalised fuzzy similarity.

    For each lineup name we take the best wage candidate above ``threshold``.
    Exact normalised-key equality always wins. Each wage name is used at most
    once (greedy, best-score-first) so two players don't collapse onto one wage.
    """
    norm_wage = {w: normalize(w) for w in wage_names}
    norm_lineup = {n: normalize(n) for n in lineup_names}

    # Candidate list of (lineup, wage, score), best first.
    scored: list[tuple[str, str, float]] = []
    wage_keys = list(norm_wage.values())
    key_to_wage: dict[str, str] = {}
    for w, k in norm_wage.items():
        key_to_wage.setdefault(k, w)  # first wins on duplicate keys

    for ln, lk in norm_lineup.items():
        if not lk:
            continue
        if lk in key_to_wage:
            scored.append((ln, key_to_wage[lk], 100.0))
            continue
        best = process.extractOne(lk, wage_keys, scorer=fuzz.WRatio)
        if best is not None:
            cand_key, score, _ = best
            scored.append((ln, key_to_wage[cand_key], float(score)))

    scored.sort(key=lambda t: t[2], reverse=True)

    pairs: dict[str, str] = {}
    scores: dict[str, float] = {}
    used_wage: set[str] = set()
    for ln, w, score in scored:
        if ln in pairs or w in used_wage:
            continue
        if score >= threshold:
            pairs[ln] = w
            scores[ln] = score
            used_wage.add(w)

    unmatched_lineup = [n for n in lineup_names if n not in pairs]
    unmatched_wage = [w for w in wage_names if w not in used_wage]
    return MatchResult(pairs, scores, unmatched_lineup, unmatched_wage)
