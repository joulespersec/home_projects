#!/usr/bin/env python3
"""
Fetch real standings from open-source datasets and write them to data/*.csv.

Run once (needs network): `python3 fetch_sources.py`. It writes the same
season,position,team schema build.py consumes, so build.py stays offline.

Sources
-------
Football (EPL, La Liga, Bundesliga, Ligue 1)
      xgabora/Club-Football-Match-Data-2000-2025 data/Matches.csv (Football-Data.co.uk
      lineage) -> league tables (3/1/0 pts, then goal difference, then goals for).
      Season derived from match date (August boundary); team names normalised
      (accent/case/punctuation-insensitive) so a club matches itself year to year.
AFL : akareen/AFL-Data-Analysis per-year match results -> ladders (4/2/0, then %).
MLB : cbwinslow/baseballdatabank core/Teams.csv -> rank within AL/NL by W-L.
NRL : uselessnrlstats cleaned_data/nrl/ladder_round_data.csv -> final ladder.
NBA : NocturneBear/NBA-Data-2010-2024 per-game data -> conference W-L standings.
F1  : muharsyad/formula-one-datasets race_results.csv + sprint_results.csv ->
      Constructors' Championship order by season points (accurate from 1991,
      when dropped-scores rules ended).
"""
import csv
import io
import os
import re
import unicodedata
import urllib.request
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RAW = "https://raw.githubusercontent.com"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def norm_key(name):
    """Accent/case/punctuation-insensitive key so a club matches itself."""
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", n.lower())


# --------------------------------------------------------------------------
# Football: one Matches.csv -> four league tables
# --------------------------------------------------------------------------
def football_tables(matches, division, allowed_counts, first_year, last_year):
    """Compute {season:'YYYY-YY' -> [teams best->worst]} for one division."""
    def season_year(d):  # European season starts in August
        y, m = int(d[:4]), int(d[5:7])
        return y if m >= 8 else y - 1

    # canonical display name = most common original spelling per key
    names = defaultdict(Counter)
    rows = [r for r in matches if r["Division"] == division]
    for r in rows:
        for t in (r["HomeTeam"], r["AwayTeam"]):
            names[norm_key(t)][t] += 1
    canon = {k: c.most_common(1)[0][0] for k, c in names.items()}

    seasons = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))  # syr -> key -> [pts,gd,gf]
    for r in rows:
        syr = season_year(r["MatchDate"])
        if not (first_year <= syr <= last_year):
            continue
        try:
            h, a = int(float(r["FTHome"])), int(float(r["FTAway"]))
        except (ValueError, KeyError):
            continue
        H, A = norm_key(r["HomeTeam"]), norm_key(r["AwayTeam"])
        s = seasons[syr]
        s[H][1] += h - a; s[H][2] += h
        s[A][1] += a - h; s[A][2] += a
        if h > a:   s[H][0] += 3
        elif a > h: s[A][0] += 3
        else:       s[H][0] += 1; s[A][0] += 1

    tables = {}
    for syr in sorted(seasons):
        s = seasons[syr]
        if len(s) not in allowed_counts:
            print(f"    {division} {syr}: {len(s)} teams — skipped (data anomaly)")
            continue
        order = sorted(s, key=lambda k: (-s[k][0], -s[k][1], -s[k][2]))
        tables[f"{syr}-{str(syr + 1)[2:]}"] = [canon[k] for k in order]
    return tables


# --------------------------------------------------------------------------
# AFL: per-year match results -> ladders
# --------------------------------------------------------------------------
def afl_ladders(years):
    tables = {}
    for y in years:
        url = f"{RAW}/akareen/AFL-Data-Analysis/main/data/matches/matches_{y}.csv"
        try:
            rows = list(csv.DictReader(io.StringIO(get(url))))
        except Exception as e:
            print(f"    AFL {y}: skip ({e})")
            continue
        pts = {}
        for row in rows:
            if not str(row["round_num"]).strip().isdigit():
                continue
            t1, t2 = row["team_1_team_name"], row["team_2_team_name"]
            try:
                s1 = int(float(row["team_1_final_goals"])) * 6 + int(float(row["team_1_final_behinds"]))
                s2 = int(float(row["team_2_final_goals"])) * 6 + int(float(row["team_2_final_behinds"]))
            except (ValueError, KeyError, TypeError):
                continue
            for t in (t1, t2):
                pts.setdefault(t, [0, 0, 0])
            pts[t1][1] += s1; pts[t1][2] += s2
            pts[t2][1] += s2; pts[t2][2] += s1
            if s1 > s2:   pts[t1][0] += 4
            elif s2 > s1: pts[t2][0] += 4
            else:         pts[t1][0] += 2; pts[t2][0] += 2
        if not pts:
            continue
        pct = lambda t: (pts[t][1] / pts[t][2]) if pts[t][2] else float("inf")
        tables[str(y)] = sorted(pts, key=lambda t: (-pts[t][0], -pct(t)))
        print(f"    AFL {y}: {len(pts)} teams, minor premier {tables[str(y)][0]}")
    return tables


# --------------------------------------------------------------------------
# MLB: Teams.csv -> rank within league by W-L
# --------------------------------------------------------------------------
def mlb_standings(years):
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
                return (-(w / (w + l) if (w + l) else 0), -(int(r["R"]) - int(r["RA"])))
            teams.sort(key=key)
            out[name][str(y)] = [r["name"] for r in teams]
    for name in lg_name.values():
        print(f"    MLB {name}: {len(out[name])} seasons")
    return out


# --------------------------------------------------------------------------
# NRL: ladder_round_data.csv -> final regular-season ladder
# --------------------------------------------------------------------------
def nrl_ladders(years):
    url = f"{RAW}/uselessnrlstats/uselessnrlstats/main/cleaned_data/nrl/ladder_round_data.csv"
    rows = [r for r in csv.DictReader(io.StringIO(get(url)))
            if r["competition_year"].startswith("NRL ")]
    by_year = defaultdict(list)
    for r in rows:
        y = int(r["year"])
        if y in years:
            by_year[y].append(r)
    tables = {}
    for y, rs in sorted(by_year.items()):
        last = max(int(r["round"]) for r in rs)
        final = sorted((r for r in rs if int(r["round"]) == last),
                       key=lambda r: int(r["ladder_position"]))
        tables[str(y)] = [r["team"] for r in final]
        print(f"    NRL {y}: {len(final)} teams, minor premier {tables[str(y)][0]}")
    return tables


# --------------------------------------------------------------------------
# NBA: per-game data -> conference standings by W-L (ties by point diff)
# --------------------------------------------------------------------------
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
    url = f"{RAW}/NocturneBear/NBA-Data-2010-2024/main/regular_season_totals_2010_2024.csv"
    rec = {}
    for r in csv.DictReader(io.StringIO(get(url))):
        k = (r["SEASON_YEAR"], r["TEAM_ID"])
        e = rec.setdefault(k, [0, 0, r["TEAM_NAME"], 0.0])
        if r["WL"] == "W": e[0] += 1
        elif r["WL"] == "L": e[1] += 1
        e[2] = r["TEAM_NAME"]
        try: e[3] += float(r["PLUS_MINUS"])
        except (ValueError, KeyError): pass
    out = {"East": {}, "West": {}}
    for s in sorted({ss for (ss, _t) in rec}):
        for conf in ("East", "West"):
            teams = [(tid, v) for (ss, tid), v in rec.items()
                     if ss == s and NBA_CONF.get(tid) == conf]
            teams.sort(key=lambda kv: (-(kv[1][0] / max(kv[1][0] + kv[1][1], 1)), -kv[1][3]))
            out[conf][s] = [v[2] for _tid, v in teams]
    print(f"    NBA: {len(out['East'])} seasons per conference")
    return out


# --------------------------------------------------------------------------
# F1: race + sprint points -> Constructors' Championship order
# --------------------------------------------------------------------------
def f1_constructors(first_year, last_year):
    base = f"{RAW}/muharsyad/formula-one-datasets/main"
    pts = defaultdict(lambda: defaultdict(float))   # season -> cid -> points
    wins = defaultdict(lambda: defaultdict(int))    # season -> cid -> wins
    names = {}                                       # cid -> name
    for fname in ("race_results.csv", "sprint_results.csv"):
        for r in csv.DictReader(io.StringIO(get(f"{base}/{fname}"))):
            try:
                yr = int(r["season"])
            except ValueError:
                continue
            if not (first_year <= yr <= last_year):
                continue
            cid = r["constructorId"]
            names[cid] = r["constructorName"]
            try: pts[yr][cid] += float(r["points"])
            except (ValueError, KeyError): pass
            if fname == "race_results.csv" and r.get("positionText") == "1":
                wins[yr][cid] += 1
    tables = {}
    for yr in sorted(pts):
        order = sorted(pts[yr], key=lambda c: (-pts[yr][c], -wins[yr][c]))
        tables[str(yr)] = [names[c] for c in order]
        print(f"    F1 {yr}: {len(order)} constructors, champion {tables[str(yr)][0]}")
    return tables


# --------------------------------------------------------------------------
def write_league(slug, tables):
    path = os.path.join(DATA_DIR, slug + ".csv")
    rows = [(season, pos, team)
            for season, order in tables.items()
            for pos, team in enumerate(order, 1)]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["season", "position", "team"])
        for r in sorted(rows, key=lambda x: (x[0], x[1])):
            w.writerow(r)
    print(f"  wrote {slug}.csv ({len(tables)} seasons)")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("Football (xgabora/Club-Football-Match-Data-2000-2025):")
    matches = list(csv.DictReader(io.StringIO(get(
        f"{RAW}/xgabora/Club-Football-Match-Data-2000-2025/main/data/Matches.csv"))))
    for slug, div, counts in [("epl", "E0", {20}), ("laliga", "SP1", {20}),
                              ("bundesliga", "D1", {18}), ("ligue1", "F1", {18, 20})]:
        tab = football_tables(matches, div, counts, 2001, 2024)
        write_league(slug, tab)

    print("AFL (akareen/AFL-Data-Analysis):")
    write_league("afl", afl_ladders(range(2001, 2026)))

    print("NRL (uselessnrlstats/uselessnrlstats):")
    write_league("nrl", nrl_ladders(set(range(2001, 2026))))

    print("NBA (NocturneBear/NBA-Data-2010-2024):")
    for conf, tab in nba_standings().items():
        write_league("nba_" + conf.lower(), tab)

    print("MLB (cbwinslow/baseballdatabank):")
    for name, tab in mlb_standings(range(2013, 2022)).items():
        write_league("mlb_" + name.lower().replace(" ", "_"), tab)

    print("F1 (muharsyad/formula-one-datasets):")
    write_league("f1", f1_constructors(2010, 2024))


if __name__ == "__main__":
    main()
