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
- A shaded band marks the **finals / playoff cut-off** (top of each panel).
- The **EPL** panel drops the relegated bottom three (they leave the division,
  so they have no "next year") and adds a **PROM** column on the right showing
  where newly *promoted* clubs finish their first season up.
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
| NBA | 0.59 | 0.35 | Stars keep good teams good (now 2005–2023; 2024–26 slot in from BBRef). |
| AFL | 0.54 | 0.29 | Moderate carry-over. |
| MLB | 0.51 | 0.26 | Whole-league W–L%: sticky but noisy over a long season. |
| NRL | 0.36 | 0.13 | As volatile as the NFL: last year barely predicts next. |
| NFL | 0.34 | 0.12 | Strongest regression — the parity machine (cap + draft). |

Concretely: an MLB team with the **best record in the league drops ~6.9
places** the next year (1st → a median 8th of 30), and the **worst climbs
~5.9**; an NFL conference winner slides several places; an NRL wooden-spooner
climbs. The EPL is the exception — champions usually stay near the top, and
**~47% of promoted clubs go straight back down** (finish in the bottom three).

## Method & scope

- **Finishing position is read within the frame teams compete in:** conference
  (NFL, NBA), a single table (EPL, AFL, NRL), or — for **MLB** — the **whole
  30-club league** ranked by win–loss % (see below).
- **Each league is restricted to a recent, stable-size era** so a position
  means the same thing every year:

  | League | Era | Teams | Grouping | Finals cut-off |
  |--------|-----|-------|----------|----------------|
  | NFL | 2002–2025 | 16 / conf | Conference | Top 7* |
  | NBA | 2005–2023‡ | 15 / conf | Conference | Top 8 |
  | MLB | 1998–2021 | 30 | Whole league, by W–L% | Top ≈10† |
  | EPL | 1995/96–2024/25 | 20 | Single table | Top 4 (UCL); bottom 3 relegated → PROM |
  | AFL | 2012–2024 | 18 | Single table | Top 8 |
  | NRL | 2007–2025 | 16→17 | Single table | Top 8 |

  \* NFL playoffs expanded from 6 to 7 per conference in 2020.
  † MLB's playoff field grew from 8 to 10 to 12 over this window; the band marks
  a representative top 10. NRL added a 17th club (the Dolphins) in 2023.
  ‡ NBA is live through 2023; the 2024–26 seasons auto-join once their
  Basketball-Reference standings are entered in `nba_bbref_manual.csv`
  (2025–26 is already in the file).

- **MLB uses win–loss % across the whole league, not divisional rank.** With 162
  games a club's record is a stable season-to-season signal, and a single 1–30
  ladder shows the pull to the mean far more clearly than five-team divisions
  (ties are broken on run differential).
- A club must appear in **both** consecutive seasons to contribute a data
  point. In the EPL the bottom three are relegated and leave the division, so
  they have no top-flight "next year"; the incoming **promoted** clubs are shown
  in the separate PROM column instead.
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
| NBA | [FiveThirtyEight nba-elo](https://github.com/fivethirtyeight/data/tree/master/nba-elo) (2005–15; 538 stopped after its ABC/Disney sale) → [sportsdataverse/hoopR-data](https://github.com/sportsdataverse/hoopR-data) ESPN game results (2016–23) → [Basketball-Reference](https://www.basketball-reference.com/leagues/) final standings (2024–26) |
| MLB | [Chadwick Baseball Databank](https://github.com/chadwickbureau/baseballdatabank) — `Teams.csv` W/L records |
| EPL | [footballcsv/england](https://github.com/footballcsv/england) + [openfootball/england](https://github.com/openfootball/england) — match results |
| AFL | [HashenAbey/afl-data-update](https://github.com/HashenAbey/afl-data-update) — match results, 1897– |
| NRL | [uselessnrlstats](https://github.com/uselessnrlstats/uselessnrlstats) — `ladder_round_data.csv` |

> **NBA sources, why three:** FiveThirtyEight's Elo data ends in 2015 (they wound
> down sports coverage after the ABC/Disney acquisition), so 2016–23 is rebuilt
> from ESPN game results mirrored by hoopR, and 2024–26 from Basketball-Reference
> standings entered by hand into `data/raw/nba_bbref_manual.csv` (that site is
> blocked by this environment's network egress policy, so it can't be fetched
> here). All three are reconciled to one team identity so year-over-year links
> survive the source boundaries.

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
data/raw/           cached source files (NBA has three: nba_allelo.csv 538,
                    nba_hoopr_games.csv ESPN, nba_bbref_manual.csv 2024-26)
data/processed/
  standings_long.csv   league, season, group, team, position, n_group, win_pct
  transitions.csv      per club: (season,pos) -> (next_season,next_pos), movement
  viz_data.json        box-plot stats + persistence metrics per league
scripts/
  build_standings.py   sources -> standardized standings, transitions, aggregates
  build_site.py        viz_data.json -> site/index.html
site/index.html        the interactive view
```
