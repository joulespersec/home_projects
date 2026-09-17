"""
Stage 2: pull notable records for each active artist from Discogs.

Reads the `active_artists` view (Spotify artists minus your exclusions),
resolves each to a Discogs artist, pulls their main master releases, enriches
them with Discogs community stats, flags the notable ones, and stores
everything in the `records` table for the Stage 3 recommender.

Usage:
    python pull_records.py                 # resolve + pull + enrich all active artists
    python pull_records.py --limit 5       # only the first 5 (handy for a trial run)
    python pull_records.py --no-enrich     # skip community-stats enrichment (faster)
    python pull_records.py --refresh-artists   # re-resolve Discogs artist matches
"""
import argparse
import datetime as dt

try:  # optional: env may also come from the shell
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from db import get_connection, init_db
from discogs_client import DiscogsClient
from matching import pick_best_artist
from scoring import flag_notable


def active_artists(conn):
    return conn.execute(
        "SELECT spotify_id, name FROM active_artists ORDER BY rank IS NULL, rank"
    ).fetchall()


def existing_match(conn, spotify_id):
    return conn.execute(
        "SELECT discogs_id, discogs_name, match_confidence FROM discogs_artists WHERE spotify_id = ?",
        (spotify_id,),
    ).fetchone()


def resolve_artist(conn, client, spotify_id, name, refresh=False):
    """Return (discogs_id, discogs_name) for an active artist, or (None, None).
    Caches the result in discogs_artists so we don't re-search every run."""
    if not refresh:
        cached = existing_match(conn, spotify_id)
        if cached is not None:
            return cached["discogs_id"], cached["discogs_name"]

    results = client.search_artist(name)
    best, confidence = pick_best_artist(name, results)
    discogs_id = best["id"] if best else None
    discogs_name = best.get("title") if best else None
    resource_url = best.get("resource_url") if best else None

    conn.execute(
        """
        INSERT INTO discogs_artists (spotify_id, discogs_id, discogs_name, resource_url, match_confidence, matched_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(spotify_id) DO UPDATE SET
            discogs_id=excluded.discogs_id,
            discogs_name=excluded.discogs_name,
            resource_url=excluded.resource_url,
            match_confidence=excluded.match_confidence,
            matched_at=excluded.matched_at
        """,
        (spotify_id, discogs_id, discogs_name, resource_url, confidence, dt.datetime.now().isoformat()),
    )
    conn.commit()
    return discogs_id, discogs_name


def collect_masters(client, discogs_id):
    """Return unique 'Main' master releases for a Discogs artist as record dicts."""
    seen = {}
    for item in client.artist_releases(discogs_id):
        if item.get("type") != "master" or item.get("role") != "Main":
            continue
        master_id = item.get("id")
        if master_id is None or master_id in seen:
            continue
        year = item.get("year")
        seen[master_id] = {
            "master_id": master_id,
            "title": item.get("title"),
            "year": year if isinstance(year, int) and year > 0 else None,
            "role": item.get("role"),
            "thumb": item.get("thumb"),
            "resource_url": item.get("resource_url"),
            "formats": None,
            "have": None,
            "want": None,
        }
    return list(seen.values())


def enrich(records, stats):
    """Merge community stats (have/want/formats) into records by master id."""
    for record in records:
        hit = stats.get(record["master_id"])
        if hit:
            record["have"] = hit.get("have")
            record["want"] = hit.get("want")
            if hit.get("formats"):
                record["formats"] = hit["formats"]
    return records


def upsert_records(conn, spotify_id, discogs_id, records, pulled_at):
    for r in records:
        conn.execute(
            """
            INSERT INTO records (master_id, spotify_id, discogs_artist_id, title, year, role,
                                 formats, thumb, resource_url, have, want, notable, pulled_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(master_id) DO UPDATE SET
                spotify_id=excluded.spotify_id,
                discogs_artist_id=excluded.discogs_artist_id,
                title=excluded.title,
                year=excluded.year,
                role=excluded.role,
                formats=COALESCE(excluded.formats, records.formats),
                thumb=excluded.thumb,
                resource_url=excluded.resource_url,
                have=COALESCE(excluded.have, records.have),
                want=COALESCE(excluded.want, records.want),
                notable=excluded.notable,
                pulled_at=excluded.pulled_at
            """,
            (
                r["master_id"], spotify_id, discogs_id, r.get("title"), r.get("year"), r.get("role"),
                r.get("formats"), r.get("thumb"), r.get("resource_url"),
                r.get("have"), r.get("want"), r.get("notable", 0), pulled_at,
            ),
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Pull notable records from Discogs for active artists.")
    parser.add_argument("--limit", type=int, help="process only the first N active artists")
    parser.add_argument("--no-enrich", action="store_true", help="skip community-stats enrichment")
    parser.add_argument("--refresh-artists", action="store_true", help="re-resolve Discogs artist matches")
    parser.add_argument("--top-n", type=int, default=None, help="notable: top-N by 'have' per artist")
    parser.add_argument("--min-have", type=int, default=None, help="notable: absolute 'have' floor")
    args = parser.parse_args()

    init_db()
    client = DiscogsClient()
    conn = get_connection()

    artists = active_artists(conn)
    if args.limit:
        artists = artists[: args.limit]

    flag_kwargs = {}
    if args.top_n is not None:
        flag_kwargs["top_n"] = args.top_n
    if args.min_have is not None:
        flag_kwargs["min_have"] = args.min_have

    pulled_at = dt.datetime.now().isoformat()
    matched = unmatched = total_records = 0

    for row in artists:
        spotify_id, name = row["spotify_id"], row["name"]
        discogs_id, discogs_name = resolve_artist(
            conn, client, spotify_id, name, refresh=args.refresh_artists
        )
        if not discogs_id:
            unmatched += 1
            print(f"  ? {name}: no Discogs match")
            continue
        matched += 1

        records = collect_masters(client, discogs_id)
        if not args.no_enrich and records:
            stats = client.search_master_stats(discogs_name or name)
            enrich(records, stats)
        flag_notable(records, **flag_kwargs)
        upsert_records(conn, spotify_id, discogs_id, records, pulled_at)

        total_records += len(records)
        notable = sum(r.get("notable", 0) for r in records)
        print(f"  + {name} -> {discogs_name}: {len(records)} records ({notable} notable)")

    conn.close()
    print(
        f"\nMatched {matched} artists ({unmatched} unmatched). "
        f"Stored {total_records} records. Run recommend.py next."
    )


if __name__ == "__main__":
    main()
