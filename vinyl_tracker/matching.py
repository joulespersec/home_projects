"""
Pure helpers for matching Spotify artist names to Discogs search results.
No network or third-party imports -- unit-testable in isolation.

Discogs disambiguates same-named artists with a trailing "(N)", e.g.
"Nirvana (2)", and its search is relevance-ordered but not always
name-exact, so we normalise both sides before comparing.
"""
import re
import unicodedata
from difflib import SequenceMatcher

# Discogs artist disambiguation suffix, e.g. "Alex G (2)".
_DISAMBIG = re.compile(r"\s*\(\d+\)\s*$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

# Below this similarity we treat a candidate as not the same artist.
FUZZY_THRESHOLD = 0.85


def _fold_accents(text):
    """Björk -> Bjork, Sigur Rós -> Sigur Ros (decompose, drop diacritics)."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_name(name):
    """Fold accents, lowercase, drop the Discogs "(N)" suffix, strip a leading
    'the', and reduce to bare alphanumerics so punctuation/spacing/diacritics
    don't matter."""
    if not name:
        return ""
    name = _DISAMBIG.sub("", name.strip())
    name = _fold_accents(name).lower()
    name = _NON_ALNUM.sub(" ", name).strip()
    if name.startswith("the "):
        name = name[4:]
    return re.sub(r"\s+", " ", name)


def similarity(a, b):
    """0..1 similarity between two already-normalized names."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def pick_best_artist(query_name, candidates):
    """
    Choose the Discogs artist result that best matches `query_name`.

    `candidates` is the list of dicts from a Discogs `type=artist` search
    (each has at least "title", "id"; "resource_url" optional). Discogs
    returns them relevance-ordered, so we keep that order as the tie-break.

    Returns (candidate, confidence):
      - ("exact")  a normalized-equal name match
      - ("fuzzy")  best similarity >= FUZZY_THRESHOLD
      - (None, "none") when nothing is close enough
    """
    target = normalize_name(query_name)
    best = None
    best_score = 0.0

    for cand in candidates or []:
        cand_norm = normalize_name(cand.get("title", ""))
        if cand_norm == target and target:
            return cand, "exact"
        score = similarity(target, cand_norm)
        if score > best_score:
            best, best_score = cand, score

    if best is not None and best_score >= FUZZY_THRESHOLD:
        return best, "fuzzy"
    return None, "none"
