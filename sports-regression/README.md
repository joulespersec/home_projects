# Regression to the mean vs consistency in pro sports

How much does a team's regular-season finishing position predict *next* season's
finish? This project builds the exact view of that question described below:

> **X axis** = this season's finishing position · **Y axis (inverted, 1 at top)** =
> next season's finishing position · one **box plot per starting position**, with
> the finals / relegation cut-offs drawn on.

Open **`index.html`** in a browser (it is fully self-contained — no server, no
external requests). Tabs switch leagues; conference leagues (NBA, MLB) have
East/West sub-tabs. `#EPL`, `#AFL`, … in the URL deep-link a league.

## How to read it

- **Boxes on the dashed diagonal (y = x)** → teams finish where they did last year:
  *consistency*.
- **Boxes pulled toward mid-table** — top finishers drifting down, bottom finishers
  drifting up → *regression to the mean*.
- Shaded green = qualification zone (finals / play-offs / Champions League); shaded
  red = relegation. In promotion/relegation leagues (EPL) the bottom columns are
  empty because those teams left the division.
- Headline KPIs per league: number of seasons, the **year-to-year rank correlation**
  (higher = stickier), and the **average absolute positions moved**.

## Leagues & how "finishing position" is defined

| League | Position rule | Finals / cut-off | Data |
|---|---|---|---|
| **EPL** | Final league-table position | Top 4 (UCL); bottom 3 relegated | **Real** (hand-verified, 2010‑11 → 2023‑24) |
| **AFL** | Home-and-away ladder (4/2/0 pts, then %) | Top 8 finals | **Real** (ladders computed from match results, 2013 → 2024) |
| **NBA** | Conference seed by W‑L record | Top 6 direct, top 10 play-in | *Illustrative* (awaiting source) |
| **MLB** | Rank within league by W‑L record | Top 6 playoffs | *Illustrative* (awaiting source) |
| **NRL** | Regular-season ladder position | Top 8 finals | *Illustrative* (awaiting source) |

NFL was intentionally dropped: too few games (≈17) makes year-to-year position too
noisy to compare against the longer seasons here.

### Real vs illustrative

Only leagues marked **Real** use verified results. The *illustrative* leagues use a
transparent latent-strength model (persistence + noise, re-ranked each year) so the
view is populated and every league-type (conference splits, finals lines) is
demonstrated — they are **not** historical results and are labelled as such in the UI.

Swapping in real data is a one-liner: drop a verified `season,position,team` CSV into
`data/<league>.csv`, set that league's `confidence` to `"real"` in `build.py`, and
re-run `python3 build.py`.

## Data pipeline

```
fetch_sources.py   # (needs network) pulls open datasets -> data/*.csv
build.py           # (offline) reads data/*.csv -> standings.json, index.html, summary.md
```

- **`data/*.csv`** is the source of truth: `season,position,team`, one row per team
  per season, positions `1..N` with no gaps.
- **`build.py`** computes each starting position's next-year distribution (quartiles,
  whiskers, outliers, mean, average move), handles promotion/relegation (teams that
  leave a division are counted but have no next-year position), and writes everything.
- **`summary.md`** is the same statistics as a plain table per league.

### Sources

- **AFL** — [akareen/AFL-Data-Analysis](https://github.com/akareen/AFL-Data-Analysis)
  (per-year match results; ladders derived here). Validated: 11/11 minor premiers
  match the official record.
- **EPL** — hand-verified final tables.

## Reproduce

```bash
pip install numpy
python3 fetch_sources.py   # optional; refreshes real-data CSVs from source
python3 build.py           # regenerates index.html, standings.json, summary.md
```
