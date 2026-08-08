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
MLB : cbwinslow/baseballdatabank core/Teams.csv (Chadwick Bureau / Retrosheet
      lineage) -> rank within league (AL/NL) by win pct, tie-break run diff.
NRL : uselessnrlstats/uselessnrlstats cleaned_data/nrl/ladder_round_data.csv
      -> final regular-season ladder (position at each season's last round).
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


def mlb_standings(years):
    """Return {'American League':{season:[teams]}, 'National League':{...}}."""
    url = f"{RAW}/cbwinslow/baseballdatabank/master/core/Teams.csv"
    rows = list(csv.DictReader(io.StringIO(get(url))))
    lg_name = {"AL": "American League", "NL": "National League"}
    out = {v: {} for v in lg_name.values()}
    for y in years:
        for lg, name in lg_name.items():
            teams = [r for r in rows if r["yearID"] == str(y) and r["lgID"] == lg]
            if not teams:
                continue
            def key(r):
                w, l = int(r["W"]), int(r["L"])
                wpct = w / (w + l) if (w + l) else 0
                diff = int(r["R"]) - int(r["RA"])
                return (-wpct, -diff)
            teams.sort(key=key)
            out[name][str(y)] = [r["name"] for r in teams]
        got = {name: len(out[name].get(str(y), [])) for name in lg_name.values()}
        print(f"  MLB {y}: AL {got['American League']}, NL {got['National League']} teams")
    return out


def nrl_ladders(years):
    """Final regular-season NRL ladder per season (position at last round)."""
    url = f"{RAW}/uselessnrlstats/uselessnrlstats/main/cleaned_data/nrl/ladder_round_data.csv"
    rows = [r for r in csv.DictReader(io.StringIO(get(url)))
            if r["competition_year"].startswith("NRL ")]
    by_year = {}
    for r in rows:
        y = int(r["year"])
        if y not in years:
            continue
        by_year.setdefault(y, []).append(r)
    tables = {}
    for y, rs in sorted(by_year.items()):
        last = max(int(r["round"]) for r in rs)
        final = [r for r in rs if int(r["round"]) == last]
        final.sort(key=lambda r: int(r["ladder_position"]))
        tables[str(y)] = [r["team"] for r in final]
        print(f"  NRL {y}: round {last}, {len(final)} teams, minor premier {tables[str(y)][0]}")
    return tables


# NBA franchise (stable TEAM_ID) -> conference, fixed across 2010-2024
# (no team changed conference in this window).
NBA_CONF = {
    "1610612737": "East", "1610612738": "East", "1610612739": "East",
    "1610612741": "East", "1610612748": "East", "1610612749": "East",
    "1610612751": "East", "1610612752": "East", "1610612753": "East",
    "1610612754": "East", "1610612755": "East", "1610612761": "East",
    "1610612764": "East", "1610612765": "East", "1610612766": "East",
    "1610612740": "West", "1610612742": "West", "1610612743": "West",
    "1610612744": "West", "1610612745": "West", "1610612746": "West",
    "1610612747": "West", "1610612750": "West", "1610612756": "West",
    "1610612757": "West", "1610612758": "West", "1610612759": "West",
    "1610612760": "West", "1610612762": "West", "1610612763": "West",
}


def nba_standings():
    """Conference standings by W-L record from per-game regular-season data."""
    url = f"{RAW}/NocturneBear/NBA-Data-2010-2024/main/regular_season_totals_2010_2024.csv"
    rec = {}  # (season, team_id) -> [wins, losses, name, plus_minus_sum]
    for r in csv.DictReader(io.StringIO(get(url))):
        k = (r["SEASON_YEAR"], r["TEAM_ID"])
        e = rec.setdefault(k, [0, 0, r["TEAM_NAME"], 0.0])
        if r["WL"] == "W": e[0] += 1
        elif r["WL"] == "L": e[1] += 1
        e[2] = r["TEAM_NAME"]
        try: e[3] += float(r["PLUS_MINUS"])
        except (ValueError, KeyError): pass
    out = {"East": {}, "West": {}}
    seasons = sorted({s for (s, _t) in rec})
    for s in seasons:
        for conf in ("East", "West"):
            teams = [(tid, v) for (ss, tid), v in rec.items()
                     if ss == s and NBA_CONF.get(tid) == conf]
            # rank by win pct, then season point differential (ties -> better diff first);
            # a documented proxy for NBA's official head-to-head tiebreakers.
            teams.sort(key=lambda kv: (-(kv[1][0] / max(kv[1][0] + kv[1][1], 1)), -kv[1][3]))
            out[conf][s] = [v[2] for _tid, v in teams]
        print(f"  NBA {s}: East {len(out['East'][s])}, West {len(out['West'][s])} teams")
    return out


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

    print("MLB (cbwinslow/baseballdatabank):")
    mlb = mlb_standings(range(2013, 2022))  # 15-team AL & NL era; data caps at 2021
    for name, tab in mlb.items():
        if tab:
            write_league("mlb_" + name.lower().replace(" ", "_"), tab)

    print("NRL (uselessnrlstats/uselessnrlstats):")
    nrl = nrl_ladders(set(range(2010, 2025)))
    if nrl:
        write_league("nrl", nrl)

    print("NBA (NocturneBear/NBA-Data-2010-2024):")
    nba = nba_standings()
    for conf, tab in nba.items():
        if tab:
            write_league("nba_" + conf.lower(), tab)


if __name__ == "__main__":
    main()
