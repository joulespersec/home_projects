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

-- ---------------------------------------------------------------------------
-- Stage 3: Last.fm complement engine (suggestions)
-- ---------------------------------------------------------------------------

-- A recomputed snapshot of artists to explore next: artists similar to your
-- active ones that you don't already listen to. Rebuilt each `recommend.py`
-- run (the table is cleared first), so it always reflects the current DB.
CREATE TABLE IF NOT EXISTS suggestions (
    name TEXT PRIMARY KEY,          -- suggested (new) artist name
    mbid TEXT,                      -- MusicBrainz id, when Last.fm provides one
    url TEXT,                       -- Last.fm page
    score REAL,                     -- aggregated match-weighted score
    seed_count INTEGER,             -- how many of your artists point here
    reasons TEXT,                   -- "because you listen to ..." seed names
    computed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_suggestions_score ON suggestions (score DESC);

-- Optional: notable records for suggested artists (populated by
-- `recommend.py --with-records`). Kept separate from `records` because
-- suggested artists are not in the `artists` table.
CREATE TABLE IF NOT EXISTS suggested_records (
    master_id INTEGER PRIMARY KEY,
    suggestion_name TEXT,           -- which suggested artist this belongs to
    discogs_artist_id INTEGER,
    title TEXT,
    year INTEGER,
    formats TEXT,
    thumb TEXT,
    resource_url TEXT,
    have INTEGER,
    want INTEGER,
    notable INTEGER DEFAULT 0,
    pulled_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_suggested_records_name ON suggested_records (suggestion_name);
