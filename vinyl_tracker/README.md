# Record Tracker -- Spotify Artist Pull + Cleanse

Stage 1 of the pipeline: pull your Spotify top artists locally, then filter
out household listening (kids' shows, background Sonos plays) before it
feeds the notable-records pull and complement recommender in later stages.

## Setup

1. Create a Spotify app: https://developer.spotify.com/dashboard
   - Add redirect URI: `http://127.0.0.1:8888/callback`
   - Note: as of the Feb 2026 changes, Development Mode requires the app
     owner's Spotify account to have Premium.
2. `cp .env.example .env` and fill in your client ID/secret.
3. `pip install -r requirements.txt`

## Run

```
python pull_top_artists.py    # authorizes on first run (opens browser), pulls top artists
python cleanse_artists.py     # interactive keep/exclude pass
```

Re-run `pull_top_artists.py` periodically. New artists land as
`reviewed = 0`, so `cleanse_artists.py` only surfaces the new ones each
time -- your exclusion list persists.

## What's stored

- `artists` -- every artist pulled, across all three Spotify time windows
- `excluded_artists` -- your exclusion list (persists across pulls)
- `active_artists` (view) -- artists minus exclusions. Downstream stages
  (Discogs notable-records pull, Last.fm complement engine) should read
  from this view, not `artists` directly.

## Known Spotify API constraints (Feb 2026)

- `popularity` may come back null -- Spotify stripped it from some artist
  responses; the code treats it as optional.
- No related-artists/recommendations access for new apps (killed Nov 2024,
  no replacement) -- that's why the complement engine is being built on
  Last.fm instead, in the next stage.
