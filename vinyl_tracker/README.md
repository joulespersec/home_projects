# Record Tracker -- Vinyl suggestions from your listening

Turns what you actually listen to on Spotify into a ranked list of records
worth owning. The pipeline runs in stages:

```
Stage 1  Spotify top artists  ->  cleanse  ->  active_artists view
Stage 2  active_artists  ->  Discogs notable-records pull  ->  records
Stage 3  active_artists + records  ->  Last.fm complement engine  ->  suggestions
```

Everything is local: a SQLite DB (`record_tracker.db`) and a handful of
scripts. Secrets (`.env`) and the DB are git-ignored.

## Setup

1. Create a Spotify app: https://developer.spotify.com/dashboard
   - Add redirect URI: `http://127.0.0.1:8888/callback`
   - Note: as of the Feb 2026 changes, Development Mode requires the app
     owner's Spotify account to have Premium.
2. `cp .env.example .env` and fill in your client ID/secret.
3. `pip install -r requirements.txt`

For Stage 2 you also need a Discogs token (see `.env.example`):
Discogs -> Settings -> Developers -> generate a personal token.

## Run

### Stage 1 -- Spotify pull + cleanse
```
python pull_top_artists.py    # authorizes on first run (opens browser), pulls top artists
python cleanse_artists.py     # interactive keep/exclude pass
```

Re-run `pull_top_artists.py` periodically. New artists land as
`reviewed = 0`, so `cleanse_artists.py` only surfaces the new ones each
time -- your exclusion list persists.

### Stage 2 -- Discogs notable-records pull
```
python pull_records.py                # resolve artists + pull records + enrich
python pull_records.py --limit 5      # trial run over the first 5 active artists
python pull_records.py --no-enrich    # skip community-stats enrichment (faster)
python pull_records.py --refresh-artists   # re-resolve Discogs artist matches
```

For each active artist this resolves a Discogs artist id (fuzzy-matched, with
accent/`(N)`-suffix handling), pulls their `Main` master releases, and enriches
them with Discogs community `have`/`want` counts. Records clearing a `have`
floor -- or ranking in an artist's top few -- are flagged `notable`. Tune the
thresholds with `--top-n` / `--min-have`.

## What's stored

- `artists` -- every artist pulled, across all three Spotify time windows
- `excluded_artists` -- your exclusion list (persists across pulls)
- `active_artists` (view) -- artists minus exclusions. Downstream stages read
  from this view, not `artists` directly.
- `discogs_artists` -- Spotify artist -> Discogs artist id mapping + match
  confidence (cached, so re-runs don't re-search)
- `records` -- notable master releases per active artist, with community
  stats and the `notable` flag

## Tests

Pure logic (name matching, notability scoring) and the SQL schema are covered
by stdlib `unittest` -- no network or API keys needed:

```
python -m unittest discover -s tests
```

## Known Discogs constraints

- Community `have`/`want` come from the `type=master` search results; a record
  Discogs doesn't return there keeps null stats (and won't be notable on its
  own). Re-running enrichment later fills them in without clobbering existing
  values.
- Authenticated requests are rate-limited to 60/min; the client paces itself
  and honours `Retry-After`.

## Known Spotify API constraints (Feb 2026)

- `popularity` may come back null -- Spotify stripped it from some artist
  responses; the code treats it as optional.
- No related-artists/recommendations access for new apps (killed Nov 2024,
  no replacement) -- that's why the complement engine is being built on
  Last.fm instead, in the next stage.
