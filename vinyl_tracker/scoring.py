"""
Pure helpers for flagging which of an artist's records count as "notable".
No network or third-party imports -- unit-testable in isolation.

Notability is driven by the Discogs community `have` count (how many people
own the record), which is the best proxy Discogs exposes for how essential a
release is. A record is flagged notable when EITHER:
  - its `have` clears an absolute floor (MIN_HAVE), so genuinely popular
    records always qualify; OR
  - it ranks in an artist's top-N by `have`, so even a niche artist still
    contributes their few best-known records to the suggestion pool.

Records with no `have` (enrichment skipped/unavailable) are treated as 0 and
are never notable on their own.
"""

DEFAULT_TOP_N = 5
DEFAULT_MIN_HAVE = 2000


def _have(record):
    value = record.get("have")
    return value if isinstance(value, int) else 0


def flag_notable(records, top_n=DEFAULT_TOP_N, min_have=DEFAULT_MIN_HAVE):
    """
    Set `notable` (0/1) on each record dict for a SINGLE artist's records.
    Mutates and also returns the list. `top_n` <= 0 disables the ranked path.
    """
    ranked = sorted(records, key=_have, reverse=True)
    top_ids = {id(r) for r in ranked[:top_n]} if top_n > 0 else set()

    for record in records:
        by_floor = _have(record) >= min_have
        by_rank = id(record) in top_ids and _have(record) > 0
        record["notable"] = 1 if (by_floor or by_rank) else 0
    return records


def suggestion_score(record):
    """
    A single comparable score for ranking records in a suggestion list.
    `want` (demand) is weighted alongside `have` (ownership) so sought-after
    records that few people have still surface. Pure and total-orderable.
    """
    have = _have(record)
    want = record.get("want")
    want = want if isinstance(want, int) else 0
    return have + 2 * want
