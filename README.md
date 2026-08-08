# Regression to the mean vs. consistency in pro sports

An analysis and interactive view of **year-on-year regular-season finishing
position** across six professional leagues — how far a club's finish predicts
where it lands the following year, and how strongly each league pulls everyone
back toward the middle.

Leagues: **NFL**, **NBA**, **MLB** (USA), **EPL** (England), **AFL** and
**NRL** (Australia). Post-season is excluded throughout — this is about the
regular-season table only.

## The view

`site/index.html` is a self-contained interactive page (no external assets).
For each league it draws a **box plot per finishing position**:

- **X axis** — this season's finishing position.
- **Y axis** — the *next* season's finishing position, **inverted (1st at the
  top)**, as requested.
- Each box is the middle 50% (Q1–Q3) with the median line and a mean diamond;
  whiskers show the full observed range.
- A dashed **diagonal** marks "finished exactly where it started." Boxes bend
  away from it toward mid-table — that bend *is* regression to the mean.
- Shaded bands mark the **finals / playoff cut-off** (top of each panel) and
  **EPL relegation** (bottom three).
- Toggles: overlay every individual team-season, the median trend line, and a
  full data table. Light/dark aware.

Open it directly in a browser, or regenerate it with the scripts below.

## Headline findings

Persistence is measured as the correlation *r* between a club's finishing
position and its position the next year (normalised to a shared 0–1 scale so
leagues of different size compare). **High r = consistency; low r = strong
regression to the mean.**

| League | r | r² | Read |
|--------|----|----|------|
| EPL | 0.67 | 0.45 | Order persists most — money and squad depth carry over. |
| NBA | 0.59 | 0.35 | Stars keep good teams good. |
| AFL | 0.54 | 0.29 | Moderate carry-over. |
| MLB | 0.47 | 0.22 | Divisions are sticky but noisy. |
| NFL | 0.34 | 0.12 | Strongest regression — the parity machine (cap + draft). |
| NRL | 0.34 | 0.11 | As volatile as the NFL: last year barely predicts next. |

Concretely: an NFL team that finishes **1st in its conference drops ~4.4
places on average** the next year; an NRL team that finishes **last climbs
~6.2 places**. The EPL is the exception — champions usually stay near the top.

## Method & scope

- **Finishing position is read within the frame teams compete in:** conference
  (NFL, NBA), division (MLB), or a single table (EPL, AFL, NRL).
- **Each league is restricted to a recent, stable-size era** so a position
  means the same thing every year:

  | League | Era | Teams | Grouping | Finals cut-off |
  |--------|-----|-------|----------|----------------|
  | NFL | 2002–2025 | 16 / conf | Conference | Top 7* |
  | NBA | 2005–2015 | 15 / conf | Conference | Top 8 |
  | MLB | 1995–2021 | ~5 / div | Division | 1st (division title)† |
  | EPL | 1995/96–2024/25 | 20 | Single table | Top 4 (UCL); bottom 3 relegated |
  | AFL | 2012–2024 | 18 | Single table | Top 8 |
  | NRL | 2007–2022 | 16 | Single table | Top 8 |

  \* NFL playoffs expanded from 6 to 7 per conference in 2020.
  † MLB's 2nd/3rd-place clubs often reach the post-season via wild cards.

- A club must appear in **both** consecutive seasons to contribute a data
  point. In the EPL the bottom three are relegated, so positions 18–20 have
  essentially no top-flight "next year" (the shaded band).
- EPL / AFL / NRL tables are **recomputed from match results** (points, then
  goal difference / percentage). Administrative points deductions are *not*
  applied — positions reflect on-field results.
- NFL/NBA positions are ranked by win % with point differential as the
  tie-break; this is a record-based finishing order, not the official playoff
  seeding (which can invert a division winner and a wild card).

## Data sources

All fetched from public GitHub repositories (cached under `data/raw/`):

| League | Source |
|--------|--------|
| NFL | [nflverse/nfldata](https://github.com/nflverse/nfldata) — game results |
| NBA | [FiveThirtyEight nba-elo](https://github.com/fivethirtyeight/data/tree/master/nba-elo) — game results, 1947–2015 |
| MLB | [Chadwick Baseball Databank](https://github.com/chadwickbureau/baseballdatabank) — `Teams.csv` divisional rank |
| EPL | [footballcsv/england](https://github.com/footballcsv/england) + [openfootball/england](https://github.com/openfootball/england) — match results |
| AFL | [HashenAbey/afl-data-update](https://github.com/HashenAbey/afl-data-update) — match results, 1897– |
| NRL | [uselessnrlstats](https://github.com/uselessnrlstats/uselessnrlstats) — `ladder_round_data.csv` |

## Rebuilding

```bash
pip install pandas numpy matplotlib   # numpy/pandas optional; stdlib is enough
# 1. (optional) re-download raw sources — see the URLs above / data/raw/
# 2. compute standings, transitions and aggregates:
python3 scripts/build_standings.py
# 3. regenerate the interactive page from the processed data:
python3 scripts/build_site.py
```

## Repository layout

```
data/raw/           cached source files (one per league)
data/processed/
  standings_long.csv   league, season, group, team, position, n_group, win_pct
  transitions.csv      per club: (season,pos) -> (next_season,next_pos), movement
  viz_data.json        box-plot stats + persistence metrics per league
scripts/
  build_standings.py   sources -> standardized standings, transitions, aggregates
  build_site.py        viz_data.json -> site/index.html
site/index.html        the interactive view
```
