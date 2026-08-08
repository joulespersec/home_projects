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

| League | Position rule | Finals / cut-off | Data (all real) |
|---|---|---|---|
| **EPL** | Final league-table position | Top 4 (UCL); bottom 3 relegated | Hand-verified, 2010‑11 → 2023‑24 (14 seasons) |
| **NBA** | Conference seed by W‑L record (ties by point diff) | Top 8; top 10 play-in (2020+) | 2010‑11 → 2023‑24 (14), East & West |
| **MLB** | Rank within league (AL/NL) by W‑L record | Top 5 playoffs (2013‑21 era) | 2013 → 2021 (9), AL & NL |
| **AFL** | Home-and-away ladder (4/2/0 pts, then %) | Top 8 finals | 2013 → 2024 (12), computed from match results |
| **NRL** | Regular-season ladder position | Top 8 finals | 2010 → 2024 (15), 16→17 teams |

NFL was intentionally dropped: too few games (≈17) makes year-to-year position too
noisy to compare against the longer seasons here.

### Headline finding

The year-to-year rank correlation separates **sticky** leagues (NBA ≈ 0.74, EPL ≈ 0.72
— where money and squad depth persist) from **volatile** ones (MLB ≈ 0.35 — strong
regression to the mean), with AFL/NRL in between (≈ 0.4–0.5). The box plots show it
directly: sticky leagues track the diagonal; volatile leagues collapse toward mid-table.

### Adding or correcting data

`data/<league>.csv` is the source of truth (`season,position,team`). Re-pull the real
sources any time with `python3 fetch_sources.py`, or hand-edit a CSV, then
`python3 build.py`. If a league's CSV is ever missing, `build.py` falls back to a
clearly-labelled illustrative model and marks it as such in the UI, so the provenance
badge never overstates the data.

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

- **EPL** — hand-verified final tables (2010‑11 → 2023‑24).
- **NBA** — [NocturneBear/NBA-Data-2010-2024](https://github.com/NocturneBear/NBA-Data-2010-2024)
  (per-game regular-season data). Conference standings by W‑L; #1 seeds validated 28/28.
- **MLB** — [cbwinslow/baseballdatabank](https://github.com/cbwinslow/baseballdatabank)
  `core/Teams.csv` (Chadwick Bureau / Retrosheet lineage). Rank within AL/NL by W‑L.
- **AFL** — [akareen/AFL-Data-Analysis](https://github.com/akareen/AFL-Data-Analysis)
  (per-year match results; ladders derived here). Validated 12/12 minor premiers.
- **NRL** — [uselessnrlstats/uselessnrlstats](https://github.com/uselessnrlstats/uselessnrlstats)
  `cleaned_data/nrl/ladder_round_data.csv`. Validated 15/15 minor premiers.

All pulled from open GitHub-hosted datasets via `fetch_sources.py`.

## Reproduce

```bash
pip install numpy
python3 fetch_sources.py   # optional; refreshes real-data CSVs from source
python3 build.py           # regenerates index.html, standings.json, summary.md
```
