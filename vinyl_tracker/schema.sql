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

-- ---------------------------------------------------------------------------
-- Stage 2: Discogs notable-records pull
-- ---------------------------------------------------------------------------

-- Resolves each active Spotify artist to a Discogs artist id. Kept separate
-- from `artists` so a re-pull of Spotify data never clobbers the mapping.
CREATE TABLE IF NOT EXISTS discogs_artists (
    spotify_id TEXT PRIMARY KEY,        -- links back to artists.spotify_id
    discogs_id INTEGER,                 -- Discogs artist id (null if unmatched)
    discogs_name TEXT,                  -- name as it appears on Discogs
    resource_url TEXT,
    match_confidence TEXT,              -- 'exact' | 'fuzzy' | 'none'
    matched_at TEXT
);

-- One row per Discogs master release (an album, format-agnostic) belonging to
-- an active artist. `have`/`want` are Discogs community counts and drive the
-- notability flag; they may be null when enrichment is skipped or unavailable.
CREATE TABLE IF NOT EXISTS records (
    master_id INTEGER PRIMARY KEY,      -- Discogs master id
    spotify_id TEXT,                    -- owning active artist
    discogs_artist_id INTEGER,
    title TEXT,
    year INTEGER,
    role TEXT,                          -- Discogs role, e.g. 'Main'
    formats TEXT,                       -- comma-joined, e.g. 'Vinyl,LP,Album'
    thumb TEXT,
    resource_url TEXT,
    have INTEGER,                       -- community.have (notability signal)
    want INTEGER,                       -- community.want
    notable INTEGER DEFAULT 0,          -- computed flag (see scoring.py)
    pulled_at TEXT,
    FOREIGN KEY (spotify_id) REFERENCES artists (spotify_id)
);

CREATE INDEX IF NOT EXISTS idx_records_spotify_id ON records (spotify_id);
CREATE INDEX IF NOT EXISTS idx_records_notable ON records (notable);
