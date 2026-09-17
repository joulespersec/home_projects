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

For Stage 2 you also need a Discogs token, and for Stage 3 a Last.fm API key
(both in `.env.example`):
- Discogs -> Settings -> Developers -> generate a personal token.
- Last.fm -> https://www.last.fm/api/account/create.

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

### Stage 3 -- Last.fm suggestions
```
python recommend.py                   # rebuild the ranked suggestion list
python recommend.py --top 25          # keep/show the top 25
python recommend.py --seed-limit 30   # seed only from your top 30 artists
python recommend.py --with-records    # also pull Discogs records for top suggestions
```

Seeds from your `active_artists`, asks Last.fm for each seed's similar artists,
and aggregates them into a ranked list: a suggestion scores higher when several
of your artists -- or a top-ranked one -- point to it. Anything already in your
library or exclusion list is filtered out. `--with-records` then pulls notable
Discogs records for the top suggestions, so you get concrete records to hunt for,
not just artist names. The list is a snapshot: each run clears and rebuilds it.

## What's stored

- `artists` -- every artist pulled, across all three Spotify time windows
- `excluded_artists` -- your exclusion list (persists across pulls)
- `active_artists` (view) -- artists minus exclusions. Downstream stages read
  from this view, not `artists` directly.
- `discogs_artists` -- Spotify artist -> Discogs artist id mapping + match
  confidence (cached, so re-runs don't re-search)
- `records` -- notable master releases per active artist, with community
  stats and the `notable` flag
- `suggestions` -- ranked artists to explore next (rebuilt each run)
- `suggested_records` -- notable records for suggested artists
  (`recommend.py --with-records`)

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
  no replacement) -- that's why the Stage 3 complement engine runs on Last.fm
  (`artist.getSimilar`) instead.
