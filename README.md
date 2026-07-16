# Multi-League Position Pay Index (`paypx`)

For each club's starting XI, compute every player's salary as an **index vs. the
team median** (median = 1.00), then average that index **by position across a
league**, so leagues can be compared at two levels:

- **Broad:** GK · DEF · MID · FWD
- **Granular:** GK · CB · FB · DM · CM · AM · W · ST

Because the index is *relative within each team*, it strips out cross-league
wage-level and currency differences and isolates **how clubs distribute pay
across positions**.

---

## ⚠️ Read this first: data-source access

The three sources named in the brief — **salaryleaks.com**, **fbref.com**,
**transfermarkt.com** — are **not reachable from the cloud build environment**:

1. The environment's egress policy is a strict allowlist (only GitHub + package
   registries); those hosts are blocked at the proxy.
2. The sites also sit behind Cloudflare-style anti-bot that **blocks datacenter
   IPs at the origin** — so even `WebFetch` / a headless browser may 403.

**Consequence:** the live 40-club scrape must be run in an environment where
those hosts are reachable (e.g. your local machine). Everything downstream of
scraping — matching, index computation, aggregation, charts — runs anywhere.

To prove the pipeline end-to-end here, the repo ships **curated seed data for
16 clubs** (`data/seed/`), in two confidence tiers (each file carries a
`confidence` + `provenance` field):

| tier | clubs | basis |
|------|-------|-------|
| **validated** (5) | Man City, Liverpool, Arsenal, Real Madrid, Barcelona | headline wages confirmed via search + reconstructed most-used XI |
| **estimated** (11) | Chelsea, Man Utd, Tottenham, Newcastle, Aston Villa; Atlético, Athletic, Real Sociedad, Villarreal, Betis, Sevilla | wage *tiers* anchored to public reporting; non-headline per-player figures reasoned from role/tier |

All 16 are **journalist-estimated, not a live scrape**. The `estimated` tier in
particular is *indicative* — it exists so the league aggregates have real
breadth to demonstrate. Replace everything with a real scrape
(`python -m paypx.pipeline`) before treating any number as final. The run
report (`report.json`) lists which clubs were `validated` / `estimated` /
`scraped`.

---

## Quick start

```bash
pip install -r requirements.txt

# Run on the 5 verified seed clubs (works with no network):
python -m paypx.pipeline --seed-only

# Full run (requires the sources to be reachable — see note above):
python -m paypx.pipeline --leagues epl,laliga --season 2025-26 --formation both

pytest -q      # 48 unit tests, no network needed
```

Outputs land in `data/output/`:

| file | contents |
|------|----------|
| `starting_xi.csv` | one row per XI player: club, league, position (broad+granular), salary, minutes/starts, index, formation mode |
| `index_broad.csv` / `index_granular.csv` | mean/median index by position per league, spread stats, high-spread flag |
| `charts/index_broad.png` / `index_granular.png` | EPL vs La Liga grouped bar charts |
| `sanity_check.csv` | per-club × position index for the 5 validated clubs |
| `report.json` | run manifest: clubs built/failed, unmatched players to review |

---

## Pipeline

```
scrape.py   fetch + cache raw HTML   ->  data/raw/{source}/{club}.html
parse.py    HTML -> wage & lineup records
names.py    normalise + fuzzy-join the two sources per club
build.py    select XI, compute team median + per-player index
aggregate.py  league-level mean index by position (+ variance flags)
charts.py   EPL vs La Liga comparison charts
pipeline.py orchestration CLI (parameterised by --leagues / --season / --formation)
```

Each stage is a small, testable module; `pipeline.py` wires them together.

### Caching
Every live fetch is written to `data/raw/{source}/{club_key}.html` and reused on
reruns, so re-running never re-hits the network. Delete a cached file (or pass
`force=True` to `scrape.fetch`) to refresh a single club.

### Fetch backends
`scrape.fetch(..., backend=...)` supports:
- `requests` (default) — fast, but blocked by anti-bot on the target sites.
- `playwright` — headless Chromium (`PAYPX_BACKEND=playwright`); can clear JS
  challenges. Chromium is preinstalled at `/opt/pw-browsers` in this
  environment. Higher odds than `requests` against Cloudflare, still not
  guaranteed from a datacenter IP.

---

## Design decisions (the brief's open questions, resolved)

| Question | Decision |
|----------|----------|
| **Season** | Default **2025-26** — the most recent *complete* season. 2026-27 (as literally scoped) has no played minutes yet, so no "most-used XI" exists. Override with `--season`. |
| **Formation** | Compute **both**: `actual` (most-used XI = top 11 by minutes) **and** `forced433` (a rigid 4-3-3, as a comparability robustness check). `--formation {actual,forced433,both}`. |
| **Winger vs forward** | A wide attacker is always **`W`** (granular) → **`FWD`** (broad). A central 10 is **`AM`** → **`MID`**. Applied consistently via `positions.py`. |
| **Full-backs / wing-backs** | Collapse into **`FB`** → `DEF`. |
| **DM vs CM** | Holding/anchor = `DM`; box-to-box/deep playmaker = `CM`; both → `MID`. |
| **Salary basis** | Fixed **base** salary only (weekly + annual), excluding bonuses/image rights. Weekly↔annual derived when only one is published (`annual = weekly × 52`). |
| **Currency** | Not converted — the index is relative within a team, so currency is irrelevant. (Would only matter for absolute cross-league wage-level claims, which the estimated data can't support anyway.) |
| **Median** | Team median is taken over the **matched XI players** (those with a joined salary). By construction the median player indexes to ~1.00. |
| **Loan / mid-season transfers** | A player is included iff they appear in the most-used XI (top 11 by minutes). No salary proration — full annual base is used; part-season players simply rank lower on minutes and usually fall outside the XI. |
| **Unmatched players** | Never guessed. Any XI player whose salary can't be joined is listed in `report.json` under `unmatched` for manual review, and excluded from the median/index. |

---

## Name matching

The two sources spell names differently (accents, `ø`/`ł`/`ß`, nicknames,
`Jr.`/suffixes, mononyms). `names.py`:

1. Normalises to a comparison key (accent/special-char transliteration,
   punctuation/suffix stripping, nickname aliasing).
2. Joins lineup→wage by best fuzzy score (`rapidfuzz` `WRatio`), exact-key
   matches winning outright, each wage row used at most once (greedy, best
   first).
3. Returns the unmatched names on both sides for review.

---

## Sanity check (5 validated clubs)

`data/output/sanity_check.csv` reports each club's index by granular position
for Man City, Liverpool, Arsenal, Real Madrid, Barcelona.

> **Note:** the brief refers to "the manual figures above/below", but **no manual
> numbers were included** in the task as received. The pipeline therefore
> *produces* the comparison table for eyeballing; to complete step 6's
> diff-against-manual, paste your manual figures and they can be asserted
> automatically (see `tests/` for the pattern).

What the seed run shows (directionally, and consistent with well-known wage
structure): **strikers** carry by far the highest index in both leagues
(Haaland/Isak/Lewandowski/Mbappé sit well above their team medians),
**full-backs** the lowest, and **wingers** show the widest cross-club spread
(Salah/Vinícius/Yamal vs. squad wingers) — flagged automatically wherever a
position's coefficient of variation ≥ 0.35.

---

## Adding leagues (Phase 2)

Add a `League` with its `Club` list to `config.LEAGUES` (Serie A, Bundesliga,
Ligue 1), fill in each club's source slugs/ids, then:

```bash
python -m paypx.pipeline --leagues seriea,bundesliga,ligue1 --season 2025-26
```

No code changes needed — the pipeline is parameterised by league and season.

---

## Repository layout

```
paypx/            pipeline package (config, positions, names, scrape, parse,
                  build, aggregate, charts, pipeline)
scripts/          make_seed.py           — regenerates the 5 validated clubs
                  make_seed_expansion.py  — regenerates the 11 estimated clubs
data/seed/        curated seed data (5 validated + 11 estimated clubs)
data/raw/         cached raw HTML from live scrapes (gitignored)
data/interim/     per-club merged tables (gitignored)
data/output/      index tables, charts, sanity check, run report
tests/            48 unit tests (no network)
```
