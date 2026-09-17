"""
Pure aggregation for the complement engine. No network or third-party imports.

Given your seed artists and the Last.fm "similar artists" for each, this
combines them into a single ranked list of artists to explore next:

  - a candidate's score is the sum, over every seed that points to it, of
    (seed weight x Last.fm match), so being recommended by several of your
    artists -- or by a top one -- pushes it up;
  - anything you already listen to or excluded is dropped;
  - candidates are merged across seeds by a normalized name so casing and
    punctuation don't create duplicates.
"""
from matching import normalize_name


def seed_weight(rank):
    """Turn a Spotify top-artist rank (1 = most-played, may be None) into a
    weight in ~[1.0, 2.0]. Better-ranked seeds pull their neighbours higher."""
    if not isinstance(rank, int) or rank < 1:
        return 1.0
    return 1.0 + max(0, 50 - rank) / 50.0


def build_suggestions(seeds, similar_by_seed, known_names, limit=None, max_reasons=3):
    """
    seeds:            list of {"name": str, "weight": float}
    similar_by_seed:  {seed_name: [{"name","match","mbid","url"}, ...]}
    known_names:      iterable of names you already listen to / excluded
                      (normalized internally) -- never suggested back
    Returns suggestions sorted by score desc, each:
        {"name","mbid","url","score","seed_count","reasons"}
    where reasons is a comma-joined list of the seeds that contributed most.
    """
    known = {normalize_name(n) for n in known_names}
    agg = {}  # normalized name -> accumulator

    for seed in seeds:
        weight = seed.get("weight", 1.0)
        for cand in similar_by_seed.get(seed["name"], []):
            norm = normalize_name(cand.get("name", ""))
            if not norm or norm in known:
                continue
            try:
                match = float(cand.get("match") or 0.0)
            except (TypeError, ValueError):
                match = 0.0
            contribution = weight * match

            entry = agg.get(norm)
            if entry is None:
                entry = {
                    "name": cand.get("name"),
                    "mbid": cand.get("mbid") or None,
                    "url": cand.get("url") or None,
                    "score": 0.0,
                    "contributions": {},  # seed name -> summed contribution
                }
                agg[norm] = entry
            entry["score"] += contribution
            entry["contributions"][seed["name"]] = (
                entry["contributions"].get(seed["name"], 0.0) + contribution
            )
            # Fill in mbid/url if a later seed had one and we didn't.
            entry["mbid"] = entry["mbid"] or (cand.get("mbid") or None)
            entry["url"] = entry["url"] or (cand.get("url") or None)

    suggestions = []
    for entry in agg.values():
        top_seeds = sorted(entry["contributions"], key=entry["contributions"].get, reverse=True)
        suggestions.append(
            {
                "name": entry["name"],
                "mbid": entry["mbid"],
                "url": entry["url"],
                "score": round(entry["score"], 6),
                "seed_count": len(entry["contributions"]),
                "reasons": ", ".join(top_seeds[:max_reasons]),
            }
        )

    suggestions.sort(key=lambda s: (s["score"], s["seed_count"], s["name"]), reverse=True)
    return suggestions[:limit] if limit else suggestions
