"""
Stage 3: the complement engine -- suggest artists (and optionally records) to
explore next, based on what you already listen to.

Seeds from the `active_artists` view, asks Last.fm for each seed's similar
artists, aggregates them into a ranked list that excludes anything already in
your library or exclusion list, and stores it in `suggestions`. With
`--with-records` it then pulls notable Discogs records for the top suggestions
into `suggested_records`, turning "artists to explore" into "records to buy".

Usage:
    python recommend.py                       # rebuild the suggestion list
    python recommend.py --top 25              # keep/show the top 25
    python recommend.py --seed-limit 30       # seed only from your top 30 artists
    python recommend.py --with-records        # also pull records for top suggestions
    python recommend.py --with-records --records-for 15
"""
import argparse
import datetime as dt

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from db import get_connection, init_db
from lastfm_client import LastfmClient
from recommender import build_suggestions, seed_weight
from scoring import flag_notable


def load_seeds(conn, seed_limit=None):
    rows = conn.execute(
        "SELECT name, rank FROM active_artists ORDER BY rank IS NULL, rank"
    ).fetchall()
    if seed_limit:
        rows = rows[:seed_limit]
    return [{"name": r["name"], "weight": seed_weight(r["rank"])} for r in rows]


def load_known_names(conn):
    """Everything you already listen to (any pulled artist) plus exclusions --
    none of it should ever be suggested back to you."""
    names = {r["name"] for r in conn.execute("SELECT name FROM artists")}
    names |= {r["name"] for r in conn.execute("SELECT name FROM excluded_artists WHERE name IS NOT NULL")}
    return names


def store_suggestions(conn, suggestions, computed_at):
    conn.execute("DELETE FROM suggestions")  # recomputed snapshot
    conn.executemany(
        """INSERT OR REPLACE INTO suggestions (name, mbid, url, score, seed_count, reasons, computed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (s["name"], s["mbid"], s["url"], s["score"], s["seed_count"], s["reasons"], computed_at)
            for s in suggestions
        ],
    )
    conn.commit()


def pull_suggested_records(conn, suggestions, records_for, flag_kwargs, computed_at):
    """For the top suggestions, resolve each on Discogs and store its notable
    records in `suggested_records`. Imported lazily so the artist-only path
    needs no Discogs token."""
    from discogs_client import DiscogsClient
    from matching import pick_best_artist
    from pull_records import collect_masters, enrich

    client = DiscogsClient()
    conn.execute("DELETE FROM suggested_records")
    total = 0

    for s in suggestions[:records_for]:
        results = client.search_artist(s["name"])
        best, confidence = pick_best_artist(s["name"], results)
        if not best:
            print(f"  ? {s['name']}: no Discogs match")
            continue
        discogs_id, discogs_name = best["id"], best.get("title")
        records = collect_masters(client, discogs_id)
        if records:
            enrich(records, client.search_master_stats(discogs_name or s["name"]))
        flag_notable(records, **flag_kwargs)

        for r in records:
            conn.execute(
                """INSERT OR REPLACE INTO suggested_records
                   (master_id, suggestion_name, discogs_artist_id, title, year, formats,
                    thumb, resource_url, have, want, notable, pulled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["master_id"], s["name"], discogs_id, r.get("title"), r.get("year"),
                    r.get("formats"), r.get("thumb"), r.get("resource_url"),
                    r.get("have"), r.get("want"), r.get("notable", 0), computed_at,
                ),
            )
        total += len(records)
        notable = sum(r.get("notable", 0) for r in records)
        print(f"  + {s['name']} -> {discogs_name}: {len(records)} records ({notable} notable)")

    conn.commit()
    print(f"Stored {total} suggested records.")


def main():
    parser = argparse.ArgumentParser(description="Suggest new artists/records from your listening.")
    parser.add_argument("--top", type=int, default=50, help="how many suggestions to keep/show")
    parser.add_argument("--seed-limit", type=int, help="seed only from your top N active artists")
    parser.add_argument("--similar-per-seed", type=int, default=50, help="similar artists per seed")
    parser.add_argument("--with-records", action="store_true", help="also pull Discogs records for top suggestions")
    parser.add_argument("--records-for", type=int, default=20, help="how many top suggestions to pull records for")
    parser.add_argument("--top-n", type=int, default=None, help="record notability: top-N by 'have'")
    parser.add_argument("--min-have", type=int, default=None, help="record notability: 'have' floor")
    args = parser.parse_args()

    init_db()
    conn = get_connection()

    seeds = load_seeds(conn, args.seed_limit)
    if not seeds:
        print("No active artists. Run pull_top_artists.py and cleanse_artists.py first.")
        conn.close()
        return
    known = load_known_names(conn)

    client = LastfmClient()
    similar_by_seed = {}
    for seed in seeds:
        similar_by_seed[seed["name"]] = client.similar_artists(seed["name"], limit=args.similar_per_seed)

    suggestions = build_suggestions(seeds, similar_by_seed, known, limit=args.top)
    computed_at = dt.datetime.now().isoformat()
    store_suggestions(conn, suggestions, computed_at)

    print(f"\nTop suggestions from {len(seeds)} seed artists:\n")
    for i, s in enumerate(suggestions[: min(len(suggestions), 25)], start=1):
        print(f"{i:>3}. {s['name']:<32} score {s['score']:.2f}  "
              f"({s['seed_count']} seed{'s' if s['seed_count'] != 1 else ''}: {s['reasons']})")

    if args.with_records:
        flag_kwargs = {}
        if args.top_n is not None:
            flag_kwargs["top_n"] = args.top_n
        if args.min_have is not None:
            flag_kwargs["min_have"] = args.min_have
        print(f"\nPulling Discogs records for the top {args.records_for} suggestions...")
        pull_suggested_records(conn, suggestions, args.records_for, flag_kwargs, computed_at)

    conn.close()


if __name__ == "__main__":
    main()
