import os
import sqlite3
import unittest

SCHEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql")


class SchemaTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        with open(SCHEMA) as f:
            self.conn.executescript(f.read())

    def tearDown(self):
        self.conn.close()

    def _add_artist(self, spotify_id, name, rank=1):
        self.conn.execute(
            "INSERT INTO artists (spotify_id, name, rank, reviewed) VALUES (?, ?, ?, 1)",
            (spotify_id, name, rank),
        )

    def test_active_artists_excludes_excluded(self):
        self._add_artist("a1", "Keeper")
        self._add_artist("a2", "Kids Show")
        self.conn.execute(
            "INSERT INTO excluded_artists (spotify_id, name) VALUES ('a2', 'Kids Show')"
        )
        names = [r["name"] for r in self.conn.execute("SELECT name FROM active_artists")]
        self.assertEqual(names, ["Keeper"])

    def test_records_roundtrip_and_notable_query(self):
        self._add_artist("a1", "Keeper")
        self.conn.execute(
            """INSERT INTO records (master_id, spotify_id, title, year, have, want, notable, pulled_at)
               VALUES (10, 'a1', 'Great Album', 1997, 5000, 300, 1, '2026-01-01')"""
        )
        self.conn.execute(
            """INSERT INTO records (master_id, spotify_id, title, notable, pulled_at)
               VALUES (11, 'a1', 'Deep Cut', 0, '2026-01-01')"""
        )
        notable = self.conn.execute(
            "SELECT title FROM records WHERE notable = 1"
        ).fetchall()
        self.assertEqual([r["title"] for r in notable], ["Great Album"])

    def test_records_upsert_coalesces_stats(self):
        self._add_artist("a1", "Keeper")
        # First insert carries stats.
        self.conn.execute(
            """INSERT INTO records (master_id, spotify_id, title, have, want, pulled_at)
               VALUES (10, 'a1', 'Album', 5000, 300, 't1')"""
        )
        # A later stat-less pull must not wipe the existing have/want.
        self.conn.execute(
            """INSERT INTO records (master_id, spotify_id, title, have, want, pulled_at)
               VALUES (10, 'a1', 'Album', NULL, NULL, 't2')
               ON CONFLICT(master_id) DO UPDATE SET
                   have=COALESCE(excluded.have, records.have),
                   want=COALESCE(excluded.want, records.want),
                   pulled_at=excluded.pulled_at"""
        )
        row = self.conn.execute("SELECT have, want, pulled_at FROM records WHERE master_id=10").fetchone()
        self.assertEqual((row["have"], row["want"], row["pulled_at"]), (5000, 300, "t2"))


if __name__ == "__main__":
    unittest.main()
