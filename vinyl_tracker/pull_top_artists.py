"""
Pulls your Spotify top artists (all three time windows) into the local DB.
Run cleanse_artists.py afterwards to filter out household/kids listening
before this feeds the notable-records pull and complement recommender.
"""
import datetime as dt

import requests

from db import get_connection, init_db
from spotify_auth import get_access_token

TIME_RANGES = ["short_term", "medium_term", "long_term"]
API_URL = "https://api.spotify.com/v1/me/top/artists"


def fetch_top_artists(token, time_range, limit=50):
    resp = requests.get(
        API_URL,
        headers={"Authorization": f"Bearer {token}"},
        params={"time_range": time_range, "limit": limit},
    )
    resp.raise_for_status()
    return resp.json()["items"]


def upsert_artist(conn, artist, time_range, rank, pulled_at):
    conn.execute(
        """
        INSERT INTO artists (spotify_id, name, genres, popularity, time_range, rank, pulled_at, reviewed)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(spotify_id) DO UPDATE SET
            name=excluded.name,
            genres=excluded.genres,
            popularity=excluded.popularity,
            time_range=excluded.time_range,
            rank=excluded.rank,
            pulled_at=excluded.pulled_at
        """,
        (
            artist["id"],
            artist["name"],
            ",".join(artist.get("genres", [])),
            artist.get("popularity"),  # may be null -- Spotify stripped this for some apps in Feb 2026
            time_range,
            rank,
            pulled_at,
        ),
    )


def main():
    init_db()
    token = get_access_token()
    conn = get_connection()
    pulled_at = dt.datetime.now().isoformat()

    total = 0
    for time_range in TIME_RANGES:
        artists = fetch_top_artists(token, time_range)
        for rank, artist in enumerate(artists, start=1):
            upsert_artist(conn, artist, time_range, rank, pulled_at)
            total += 1
        print(f"{time_range}: {len(artists)} artists")

    conn.commit()
    conn.close()
    print(f"Pulled {total} artist rows. Run cleanse_artists.py next to filter noise.")


if __name__ == "__main__":
    main()
