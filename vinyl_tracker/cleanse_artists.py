"""
Interactive pass over freshly-pulled artists to exclude household/kids
listening (the Sonos-on-repeat problem -- KPop Demon Hunters and friends)
before it pollutes the personal affinity signal used downstream.
"""
import datetime as dt

from db import get_connection


def get_unreviewed(conn):
    return conn.execute(
        """
        SELECT DISTINCT spotify_id, name, genres
        FROM artists
        WHERE reviewed = 0
        ORDER BY name
        """
    ).fetchall()


def main():
    conn = get_connection()
    rows = get_unreviewed(conn)

    if not rows:
        print("Nothing to review.")
        return

    print(f"{len(rows)} artists to review. [k]eep / [x]clude / [s]kip for later / [q]uit\n")

    for row in rows:
        answer = input(f"{row['name']} ({row['genres']}): ").strip().lower()

        if answer == "q":
            break
        elif answer == "x":
            reason = input("  reason (optional): ").strip()
            conn.execute(
                "INSERT OR REPLACE INTO excluded_artists (spotify_id, name, reason, excluded_at) VALUES (?, ?, ?, ?)",
                (row["spotify_id"], row["name"], reason, dt.datetime.now().isoformat()),
            )
            conn.execute("UPDATE artists SET reviewed = 1 WHERE spotify_id = ?", (row["spotify_id"],))
        elif answer == "k":
            conn.execute("UPDATE artists SET reviewed = 1 WHERE spotify_id = ?", (row["spotify_id"],))
        # 's' or anything else: leave reviewed = 0, comes up again next run

    conn.commit()

    active = conn.execute("SELECT COUNT(*) FROM active_artists").fetchone()[0]
    excluded = conn.execute("SELECT COUNT(*) FROM excluded_artists").fetchone()[0]
    conn.close()
    print(f"\nActive artist rows: {active} | Excluded artists: {excluded}")


if __name__ == "__main__":
    main()
