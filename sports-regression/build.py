#!/usr/bin/env python3
"""
Regression-to-mean vs consistency across pro sports leagues.

Reads final regular-season standings (one CSV per league/conference under data/),
computes year-on-year finishing-position transitions, and emits:

  * standings.json  - tidy transition statistics used by index.html
  * index.html      - self-contained interactive box-plot view
  * summary.md      - per-position range + average movement tables

Data model
----------
Each row of a standings CSV is:  season,position,team
  - `season` is the season label (sortable string, e.g. "2018-19" or "2018").
  - `position` is the FINAL regular-season finishing position (1 = best).
  - one row per team per season; positions are 1..N with no gaps.

A "transition" is a team that appears in both season Y and season Y+1 within the
same closed group (single table, or one conference/league). We record where a
team finishing position p in year Y ends up in year Y+1. Promotion/relegation
leagues (EPL) therefore have empty columns at the relegation positions - teams
there leave the division, which is itself the point.

Data confidence is declared per league in LEAGUES below and surfaced in the UI.
CSVs are the editable source of truth: replace an "illustrative" league's CSVs
with verified standings and re-run `python3 build.py` to update everything.
"""
import csv
import json
import os
from collections import defaultdict
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

# --------------------------------------------------------------------------
# Real EPL final tables, 1st -> 20th. High confidence (hand-verified).
# --------------------------------------------------------------------------
EPL = {
    "2010-11": ["Man Utd","Chelsea","Man City","Arsenal","Tottenham","Liverpool","Everton","Fulham","Aston Villa","Sunderland","West Brom","Newcastle","Stoke","Bolton","Blackburn","Wigan","Wolves","Birmingham","Blackpool","West Ham"],
    "2011-12": ["Man City","Man Utd","Arsenal","Tottenham","Newcastle","Chelsea","Everton","Liverpool","Fulham","West Brom","Swansea","Norwich","Sunderland","Stoke","Wigan","Aston Villa","QPR","Bolton","Blackburn","Wolves"],
    "2012-13": ["Man Utd","Man City","Chelsea","Arsenal","Tottenham","Everton","Liverpool","West Brom","Swansea","West Ham","Norwich","Fulham","Stoke","Southampton","Aston Villa","Newcastle","Sunderland","Wigan","Reading","QPR"],
    "2013-14": ["Man City","Liverpool","Chelsea","Arsenal","Everton","Tottenham","Man Utd","Southampton","Stoke","Newcastle","Crystal Palace","Swansea","West Ham","Sunderland","Aston Villa","Hull","West Brom","Norwich","Fulham","Cardiff"],
    "2014-15": ["Chelsea","Man City","Arsenal","Man Utd","Tottenham","Liverpool","Southampton","Swansea","Stoke","Crystal Palace","Everton","West Ham","West Brom","Leicester","Newcastle","Sunderland","Aston Villa","Hull","Burnley","QPR"],
    "2015-16": ["Leicester","Arsenal","Tottenham","Man City","Man Utd","Southampton","West Ham","Liverpool","Stoke","Chelsea","Everton","Swansea","Watford","West Brom","Crystal Palace","Bournemouth","Sunderland","Newcastle","Norwich","Aston Villa"],
    "2016-17": ["Chelsea","Tottenham","Man City","Liverpool","Arsenal","Man Utd","Everton","Southampton","Bournemouth","West Brom","West Ham","Leicester","Stoke","Crystal Palace","Swansea","Burnley","Watford","Hull","Middlesbrough","Sunderland"],
    "2017-18": ["Man City","Man Utd","Tottenham","Liverpool","Chelsea","Arsenal","Burnley","Everton","Leicester","Newcastle","Crystal Palace","Bournemouth","West Ham","Watford","Brighton","Huddersfield","Southampton","Swansea","Stoke","West Brom"],
    "2018-19": ["Man City","Liverpool","Chelsea","Tottenham","Arsenal","Man Utd","Wolves","Everton","Leicester","West Ham","Watford","Crystal Palace","Newcastle","Bournemouth","Burnley","Southampton","Brighton","Cardiff","Fulham","Huddersfield"],
    "2019-20": ["Liverpool","Man City","Man Utd","Chelsea","Leicester","Tottenham","Wolves","Arsenal","Sheffield Utd","Burnley","Southampton","Everton","Newcastle","Crystal Palace","Brighton","West Ham","Aston Villa","Bournemouth","Watford","Norwich"],
    "2020-21": ["Man City","Man Utd","Liverpool","Chelsea","Leicester","West Ham","Tottenham","Arsenal","Leeds","Everton","Aston Villa","Newcastle","Wolves","Crystal Palace","Southampton","Brighton","Burnley","Fulham","West Brom","Sheffield Utd"],
    "2021-22": ["Man City","Liverpool","Chelsea","Tottenham","Arsenal","Man Utd","West Ham","Leicester","Brighton","Wolves","Newcastle","Crystal Palace","Brentford","Aston Villa","Southampton","Everton","Leeds","Burnley","Watford","Norwich"],
    "2022-23": ["Man City","Arsenal","Man Utd","Newcastle","Liverpool","Brighton","Aston Villa","Tottenham","Brentford","Fulham","Crystal Palace","Chelsea","Wolves","West Ham","Bournemouth","Nott'm Forest","Everton","Leicester","Leeds","Southampton"],
    "2023-24": ["Man City","Arsenal","Liverpool","Aston Villa","Tottenham","Chelsea","Newcastle","Man Utd","West Ham","Crystal Palace","Brighton","Bournemouth","Fulham","Wolves","Everton","Brentford","Nott'm Forest","Luton","Burnley","Sheffield Utd"],
}

# --------------------------------------------------------------------------
# League configuration.
#   type: "single" (one table) or "conferences" (dict of closed groups)
#   cutoffs: horizontal reference lines drawn on the *next-year* (Y) axis.
#            kind "top"  -> line sits just BELOW `pos` (a "make it" threshold)
#            kind "bottom"-> line sits just ABOVE `pos` (a "drop" threshold)
# --------------------------------------------------------------------------
LEAGUES = {
    "EPL": {
        "name": "English Premier League",
        "sport": "Football (soccer)",
        "type": "single",
        "size": 20,
        "relegation": True,
        "confidence": "real",
        "position_rule": "Final league-table position (points, then goal difference).",
        "cutoffs": [
            {"pos": 4, "label": "Champions League (top 4)", "kind": "top"},
            {"pos": 7, "label": "Europe (approx.)", "kind": "top", "soft": True},
            {"pos": 17, "label": "Relegation (bottom 3)", "kind": "bottom"},
        ],
    },
    "NBA": {
        "name": "NBA",
        "sport": "Basketball",
        "type": "conferences",
        "conferences": ["East", "West"],
        "size": 15,
        "relegation": False,
        "confidence": "real",  # NocturneBear/NBA-Data-2010-2024, 2010-11 to 2023-24
        "position_rule": "Regular-season seed within conference (by W-L record, ties by point differential).",
        "cutoffs": [
            {"pos": 8, "label": "Playoffs (top 8)", "kind": "top"},
            {"pos": 10, "label": "Play-in cut (2020+, top 10)", "kind": "top", "soft": True},
        ],
        "rho": 0.55,
    },
    "MLB": {
        "name": "MLB",
        "sport": "Baseball",
        "type": "conferences",
        "conferences": ["American League", "National League"],
        "size": 15,
        "relegation": False,
        "confidence": "real",  # cbwinslow/baseballdatabank Teams.csv, 2013-2021
        "position_rule": "Rank within league (AL/NL) by win-loss record (162-game season).",
        "cutoffs": [
            {"pos": 5, "label": "Playoffs (top 5, 2013–21)", "kind": "top"},
        ],
        "rho": 0.50,
    },
    "AFL": {
        "name": "AFL",
        "sport": "Australian rules football",
        "type": "single",
        "size": 18,
        "relegation": False,
        "confidence": "real",  # ladders computed from real match results by fetch_sources.py
        "position_rule": "Final home-and-away ladder position (premiership points, then percentage).",
        "cutoffs": [
            {"pos": 8, "label": "Finals series (top 8)", "kind": "top"},
        ],
        "rho": 0.58,
    },
    "NRL": {
        "name": "NRL",
        "sport": "Rugby league",
        "type": "single",
        "size": 17,
        "relegation": False,
        "confidence": "real",  # uselessnrlstats ladder_round_data.csv, 2010-2024
        "position_rule": "Final regular-season ladder position (competition points, then differential).",
        "cutoffs": [
            {"pos": 8, "label": "Finals series (top 8)", "kind": "top"},
        ],
        "rho": 0.45,
    },
}

# Season labels used for illustrative leagues (10 seasons -> 9 transitions).
ILLUSTRATIVE_SEASONS = [str(y) for y in range(2015, 2025)]


# --------------------------------------------------------------------------
# Illustrative-data generator (clearly labelled; NOT real results).
# A latent-strength AR(1) model: each team's next-year strength regresses toward
# the mean with persistence rho plus noise, then teams are re-ranked. This
# reproduces the qualitative shape of regression-to-mean without pretending to
# be a historical record.
# --------------------------------------------------------------------------
def make_illustrative(size, seasons, rho, seed):
    rng = np.random.default_rng(seed)
    n_teams = size
    teams = [f"Team {i+1:02d}" for i in range(n_teams)]
    # latent "true strength" for each team, persistent across the whole window
    base = rng.normal(0, 1, n_teams)
    tables = {}
    strength = base.copy()
    for s in seasons:
        strength = rho * strength + np.sqrt(1 - rho * rho) * (0.7 * base + 0.3 * rng.normal(0, 1, n_teams))
        season_perf = strength + rng.normal(0, 0.85, n_teams)
        order = np.argsort(-season_perf)  # best first
        tables[s] = [teams[i] for i in order]
    return tables


# --------------------------------------------------------------------------
# CSV read/write
# --------------------------------------------------------------------------
def tables_to_rows(tables):
    rows = []
    for season, order in tables.items():
        for pos, team in enumerate(order, start=1):
            rows.append((season, pos, team))
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["season", "position", "team"])
        for r in sorted(rows, key=lambda x: (x[0], x[1])):
            w.writerow(r)


def read_csv(path):
    tables = defaultdict(dict)  # season -> pos -> team
    with open(path) as f:
        for row in csv.DictReader(f):
            tables[row["season"]][int(row["position"])] = row["team"]
    out = {}
    for season, posmap in tables.items():
        out[season] = [posmap[p] for p in sorted(posmap)]
    return out


# --------------------------------------------------------------------------
# Transition statistics
# --------------------------------------------------------------------------
def box_stats(values):
    a = np.array(sorted(values), dtype=float)
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    iqr = q3 - q1
    lo_fence, hi_fence = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    inside = a[(a >= lo_fence) & (a <= hi_fence)]
    whisker_lo = float(inside.min()) if inside.size else float(a.min())
    whisker_hi = float(inside.max()) if inside.size else float(a.max())
    outliers = [float(x) for x in a if x < whisker_lo or x > whisker_hi]
    return {
        "min": float(a.min()), "max": float(a.max()),
        "q1": float(q1), "median": float(med), "q3": float(q3),
        "whiskerLo": whisker_lo, "whiskerHi": whisker_hi,
        "outliers": outliers,
    }


def analyse_group(tables, size):
    """Return per-starting-position transition stats for one closed group."""
    seasons = sorted(tables.keys())
    # position(team) per season
    pos_of = {}
    for s in seasons:
        pos_of[s] = {team: i + 1 for i, team in enumerate(tables[s])}

    # collect next-year positions per starting position
    nexts = defaultdict(list)   # p -> [next positions]
    relegated = defaultdict(int)  # p -> count of teams that vanished next year
    for a, b in zip(seasons, seasons[1:]):
        for team, p in pos_of[a].items():
            if team in pos_of[b]:
                nexts[p].append(pos_of[b][team])
            else:
                relegated[p] += 1

    positions = []
    maxpos = max([size] + [max(pos_of[s].values()) for s in seasons])
    for p in range(1, maxpos + 1):
        vals = nexts.get(p, [])
        entry = {"pos": p, "n": len(vals), "leftDivision": relegated.get(p, 0)}
        if vals:
            arr = np.array(vals, dtype=float)
            entry.update(box_stats(vals))
            entry["meanNext"] = float(arr.mean())
            entry["meanMove"] = float((arr - p).mean())  # +ve = fell down the table
            entry["points"] = [int(v) for v in vals]
        positions.append(entry)
    return {"size": size, "seasons": seasons, "positions": positions}


# --------------------------------------------------------------------------
# Build everything
# --------------------------------------------------------------------------
def build():
    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {"generatedAt": date.today().isoformat(), "leagues": []}

    for key, cfg in LEAGUES.items():
        groups = []
        conf_names = cfg.get("conferences", [""])
        actual_conf = cfg["confidence"]  # may be downgraded if real CSV is missing
        for ci, conf in enumerate(conf_names):
            slug = key.lower() + ("" if conf == "" else "_" + conf.lower().replace(" ", "_"))
            csv_path = os.path.join(DATA_DIR, slug + ".csv")

            if key == "EPL":
                # real data embedded in this file; (re)materialise CSV if absent
                if not os.path.exists(csv_path):
                    write_csv(csv_path, tables_to_rows(EPL))
                tables = read_csv(csv_path)
            elif cfg["confidence"] == "real":
                # real data produced by fetch_sources.py; must already exist
                if os.path.exists(csv_path):
                    tables = read_csv(csv_path)
                else:
                    print(f"  ! {slug}.csv missing — run fetch_sources.py. "
                          f"Falling back to illustrative data for {key}.")
                    tables = make_illustrative(cfg["size"], ILLUSTRATIVE_SEASONS,
                                               cfg.get("rho", 0.5), seed=1000 + hash(slug) % 9000)
                    write_csv(csv_path, tables_to_rows(tables))
                    actual_conf = "illustrative"
            else:
                if not os.path.exists(csv_path):
                    tables = make_illustrative(cfg["size"], ILLUSTRATIVE_SEASONS,
                                               cfg.get("rho", 0.5), seed=1000 + hash(slug) % 9000)
                    write_csv(csv_path, tables_to_rows(tables))
                tables = read_csv(csv_path)

            stats = analyse_group(tables, cfg["size"])
            stats["key"] = conf
            stats["name"] = conf if conf else cfg["name"]
            groups.append(stats)

        payload["leagues"].append({
            "key": key,
            "name": cfg["name"],
            "sport": cfg["sport"],
            "confidence": actual_conf,
            "positionRule": cfg["position_rule"],
            "relegation": cfg["relegation"],
            "cutoffs": cfg["cutoffs"],
            "groups": groups,
        })

    with open(os.path.join(HERE, "standings.json"), "w") as f:
        json.dump(payload, f, indent=1)

    write_summary(payload)
    write_html(payload)
    print("Built standings.json, summary.md and index.html")
    return payload


def write_summary(payload):
    real = [l["name"] for l in payload["leagues"] if l["confidence"] == "real"]
    illus = [l["name"] for l in payload["leagues"] if l["confidence"] != "real"]
    prov = f"Real data: {', '.join(real)}." if real else ""
    if illus:
        prov += f" Illustrative (model, not real results): {', '.join(illus)}."
    lines = ["# Year-on-year finishing-position movement\n",
             f"_Generated {payload['generatedAt']}. {prov}_\n"]
    for lg in payload["leagues"]:
        lines.append(f"\n## {lg['name']} ({lg['sport']}) — {lg['confidence']}")
        lines.append(f"_{lg['positionRule']}_\n")
        for g in lg["groups"]:
            if g["name"] != lg["name"]:
                lines.append(f"\n### {g['name']}")
            lines.append("\n| Finish (Y) | n | Next-yr range | Median | Avg move |")
            lines.append("|---:|---:|:---:|---:|---:|")
            for e in g["positions"]:
                if e["n"] == 0:
                    rng = "— (left division)" if e["leftDivision"] else "—"
                    lines.append(f"| {e['pos']} | 0 | {rng} |  |  |")
                else:
                    mv = e["meanMove"]
                    arrow = "↓" if mv > 0.3 else ("↑" if mv < -0.3 else "→")
                    lines.append(f"| {e['pos']} | {e['n']} | {int(e['min'])}–{int(e['max'])} "
                                 f"| {e['median']:.1f} | {arrow} {mv:+.1f} |")
    with open(os.path.join(HERE, "summary.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_html(payload):
    tpl = open(os.path.join(HERE, "template.html")).read()
    html = tpl.replace("/*__DATA__*/", json.dumps(payload))
    with open(os.path.join(HERE, "index.html"), "w") as f:
        f.write(html)


if __name__ == "__main__":
    build()
