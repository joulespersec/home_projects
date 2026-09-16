CREATE TABLE IF NOT EXISTS artists (
    spotify_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    genres TEXT,
    popularity INTEGER,
    time_range TEXT,
    rank INTEGER,
    pulled_at TEXT,
    reviewed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS excluded_artists (
    spotify_id TEXT PRIMARY KEY,
    name TEXT,
    reason TEXT,
    excluded_at TEXT
);

-- Downstream stages (notable-records pull, complement engine) should
-- read from this view, not from `artists` directly.
CREATE VIEW IF NOT EXISTS active_artists AS
SELECT a.*
FROM artists a
LEFT JOIN excluded_artists e ON a.spotify_id = e.spotify_id
WHERE e.spotify_id IS NULL;
