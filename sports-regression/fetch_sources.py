#!/usr/bin/env python3
"""
Fetch real standings from open-source datasets and write them to data/*.csv.

Run once (needs network): `python3 fetch_sources.py`. It writes the same
season,position,team schema build.py consumes, so build.py stays offline.

Sources
-------
AFL : akareen/AFL-Data-Analysis  (per-year match results, MIT) -> ladders
      Ladder rule: 4 pts win / 2 draw / 0 loss, then percentage (PF/PA).
      Home-and-away games only (finals rounds have non-numeric round_num).

Other leagues can be added here as reachable sources are confirmed.
"""
import csv
import io
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RAW = "https://raw.githubusercontent.com"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def afl_ladders(years):
    """Return {season: [teams best->worst]} computed from match results."""
    tables = {}
    for y in years:
        url = f"{RAW}/akareen/AFL-Data-Analysis/main/data/matches/matches_{y}.csv"
        try:
            text = get(url)
        except Exception as e:
            print(f"  AFL {y}: skip ({e})")
            continue
        pts = {}   # team -> [premiership_points, points_for, points_against]
        rows = list(csv.DictReader(io.StringIO(text)))
        for row in rows:
            if not str(row["round_num"]).strip().isdigit():
                continue  # finals / non H&A
            t1, t2 = row["team_1_team_name"], row["team_2_team_name"]
            try:  # some seasons store scores as floats ("14.0")
                s1 = int(float(row["team_1_final_goals"])) * 6 + int(float(row["team_1_final_behinds"]))
                s2 = int(float(row["team_2_final_goals"])) * 6 + int(float(row["team_2_final_behinds"]))
            except (ValueError, KeyError, TypeError):
                continue
            for t in (t1, t2):
                pts.setdefault(t, [0, 0, 0])
            pts[t1][1] += s1; pts[t1][2] += s2
            pts[t2][1] += s2; pts[t2][2] += s1
            if s1 > s2:   pts[t1][0] += 4; pts[t2][0] += 0
            elif s2 > s1: pts[t2][0] += 4; pts[t1][0] += 0
            else:         pts[t1][0] += 2; pts[t2][0] += 2
        if not pts:
            print(f"  AFL {y}: no completed H&A games")
            continue
        def pct(t):
            pf, pa = pts[t][1], pts[t][2]
            return (pf / pa) if pa else float("inf")
        order = sorted(pts, key=lambda t: (-pts[t][0], -pct(t)))
        tables[str(y)] = order
        print(f"  AFL {y}: {len(order)} teams, minor premier {order[0]}")
    return tables


def write_league(slug, tables):
    path = os.path.join(DATA_DIR, slug + ".csv")
    rows = []
    for season, order in tables.items():
        for pos, team in enumerate(order, 1):
            rows.append((season, pos, team))
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["season", "position", "team"])
        for r in sorted(rows, key=lambda x: (x[0], x[1])):
            w.writerow(r)
    print(f"  wrote {path} ({len(tables)} seasons)")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    print("AFL (akareen/AFL-Data-Analysis):")
    afl = afl_ladders(range(2013, 2025))
    if afl:
        write_league("afl", afl)


if __name__ == "__main__":
    main()
