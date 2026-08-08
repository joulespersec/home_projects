# Regression to the mean vs consistency in pro sports

How much does a team's regular-season finishing position predict *next* season's
finish? This builds the view of that directly:

> **X axis** = this season's finishing position · **Y axis (inverted, 1 at top)** =
> next season's finishing position · one **box plot per starting position**, with
> finals / relegation cut-offs drawn on and a dashed **y = x** "no-change" diagonal.

Open **`index.html`** in a browser (fully self-contained — no server, no external
requests). Tabs switch leagues; conference leagues (NBA, MLB) get East/West
sub-tabs. `#EPL`, `#F1`, … in the URL deep-link a league.

## How to read it

- **Boxes on the diagonal** → teams finish where they did last year: *consistency*.
- **Boxes pulled toward mid-table** — top finishers drifting down, bottom finishers
  drifting up → *regression to the mean*.
- Shaded green = qualification zone (finals / play-offs / Champions League); shaded
  red = relegation.
- **Promotion/relegation leagues:** the bottom columns are empty because those teams
  were relegated. The green **“Prom.”** column on the right instead shows where the
  teams *promoted into* the division that year finished — the churn from the other side.
- KPIs per league: number of seasons, the **year-to-year rank correlation** (higher =
  stickier), and the **average absolute positions moved**.

## Leagues (all real data)

| League | Position rule | Seasons | Cut-offs |
|---|---|---|---|
| **EPL** | League table (pts, GD) | 2001–02 → 2024–25 | Top 4 UCL; bottom 3 down |
| **La Liga** | League table | 2001–02 → 2024–25 | Top 4 UCL; bottom 3 down |
| **Bundesliga** | League table (18 clubs) | 2001–02 → 2024–25 | Top 4 UCL; 16–18 down |
| **Ligue 1** | League table (20→18 in 2023-24) | 2001–02 → 2024–25 | ~Top 3 UCL; relegation |
| **NBA** | Conference seed by W-L | 2010–11 → 2023–24 | Top 8; top 10 play-in |
| **MLB** | Rank in league (AL/NL) by W-L | 2013 → 2021 | Top 5 playoffs |
| **AFL** | H&A ladder (4/2/0, then %) | 2001 → 2025 | Top 8 finals |
| **NRL** | Regular-season ladder | 2001 → 2025 | Top 8 finals |
| **F1** | Constructors' Championship (pts) | 2010 → 2024 | Podium (top 3) |

NFL was intentionally dropped — too few games (~17) make year-to-year position too
noisy to compare against the longer seasons here.

### Headline finding — the stickiness spectrum

Year-to-year rank correlation, most consistent → most volatile:

| Rank corr. | League | Read |
|---:|---|---|
| 0.84 | **F1 Constructors** | Capital & tech dominance — the champion box is a flat line at P1 |
| 0.68 | EPL | Big-six money persists |
| 0.65 | La Liga | Real/Barça/Atlético lock the top |
| 0.60 | NBA | Stars + tanking cycles |
| 0.55 | Ligue 1 / Bundesliga | PSG / Bayern at the top, churn below |
| 0.50 | AFL | Draft + salary cap pull to the mean |
| 0.43 | MLB | Long season, but strong regression |
| 0.35 | **NRL** | Salary-cap parity — last year barely predicts next |

Promotion/relegation leagues also differ in how promoted teams fare: EPL promoted
sides finish a **median 17th** (survival is the ceiling for most), while Bundesliga
promoted sides sit at **~14th** and occasionally storm the top half.

## Data pipeline

```
fetch_sources.py   # (needs network) pulls open datasets -> data/*.csv
build.py           # (offline) reads data/*.csv -> standings.json, index.html, summary.md
```

- **`data/*.csv`** is the source of truth: `season,position,team`, one row per team
  per season, positions `1..N` (N may vary by season — expansion, league resizing).
- **`build.py`** computes each starting position's next-year distribution (quartiles,
  whiskers, outliers, mean, average move). Transitions are only formed between seasons
  one year apart, so a skipped/anomalous season never creates a false multi-year jump.
  For relegation leagues it also computes the promoted-team distribution.
- Football tables are computed from match results (3/1/0, then goal difference, then
  goals for); team names are matched accent/case/punctuation-insensitively so a club
  lines up with itself year to year; a per-season team-count check drops corrupt seasons.

### Sources (all open, GitHub-hosted)

- **Football (EPL/La Liga/Bundesliga/Ligue 1)** — [xgabora/Club-Football-Match-Data-2000-2025](https://github.com/xgabora/Club-Football-Match-Data-2000-2025) (Football-Data.co.uk lineage).
- **NBA** — [NocturneBear/NBA-Data-2010-2024](https://github.com/NocturneBear/NBA-Data-2010-2024). #1 seeds validated 28/28.
- **MLB** — [cbwinslow/baseballdatabank](https://github.com/cbwinslow/baseballdatabank) `core/Teams.csv`.
- **AFL** — [akareen/AFL-Data-Analysis](https://github.com/akareen/AFL-Data-Analysis). Minor premiers validated 25/25.
- **NRL** — [uselessnrlstats/uselessnrlstats](https://github.com/uselessnrlstats/uselessnrlstats). Minor premiers validated 25/25.
- **F1** — [muharsyad/formula-one-datasets](https://github.com/muharsyad/formula-one-datasets) (Ergast lineage). Champions validated 15/15.

### Caveats
- MLB caps at 2021 (that mirror's last year); NBA at 2010–24 (that dataset's span).
- La Liga head-to-head and NBA head-to-head tiebreakers are approximated (goal
  difference / point differential) — negligible effect on the distributions.
- F1 tracks constructors by their dataset ID, so a rebrand (e.g. Racing Point →
  Aston Martin) reads as churn rather than continuity.

## Reproduce

```bash
pip install numpy
python3 fetch_sources.py   # optional; refreshes real-data CSVs from source
python3 build.py           # regenerates index.html, standings.json, summary.md
```

## Possible additions
Natural next leagues (data feasibility varies): **NHL** (ice hockey), **Serie A**,
**Eredivisie**, **Primeira Liga**, **Scottish Premiership**; **MLS** & **A-League**
(no relegation, conference/finals); **Super Rugby / Premiership Rugby / Top 14**;
**IPL / Big Bash** cricket; **EuroLeague** basketball; and motorsport siblings
**F1 drivers**, **MotoGP**, **IndyCar**, **NASCAR**.
