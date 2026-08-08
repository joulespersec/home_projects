#!/usr/bin/env python3
"""
Build standardized regular-season finishing positions for six pro leagues,
then derive year-on-year (YoY) position transitions used to study
regression-to-the-mean vs. consistency.

Sources (all fetched from GitHub, cached under data/raw/):
  NFL  nflverse/nfldata            game-by-game -> conference standings
  NBA  fivethirtyeight/data        game-by-game -> conference standings (2005-2015)
  MLB  chadwickbureau (mirror)     Teams.csv provides official divisional Rank
  EPL  footballcsv + openfootball  match results -> league table
  AFL  HashenAbey/afl-data-update  match results -> ladder
  NRL  uselessnrlstats             ladder_round_data.csv -> final ladder

Output (data/processed/):
  standings_long.csv   league, season, group, team, position, n_group, win_pct
  transitions.csv      per team: (season, pos) -> (next_season, next_pos), movement
  viz_data.json        aggregated box-plot stats per league per start position
"""
import csv, json, re, os, statistics
from collections import defaultdict

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "processed")
os.makedirs(OUT, exist_ok=True)

# ----- League configuration ------------------------------------------------
# window: inclusive [start, end] by *season end year*; chosen so team count &
# structure are stable, making an absolute finishing position comparable YoY.
LEAGUE_META = {
    "NFL": {"name": "NFL (American football)", "grouped_by": "conference",
            "size": 16, "window": (2002, 2025),
            "finals_cut": 7, "finals_label": "Playoffs (top 7)",
            "relegation_cut": None},
    "NBA": {"name": "NBA (basketball)", "grouped_by": "conference",
            "size": 15, "window": (2005, 2015),
            "finals_cut": 8, "finals_label": "Playoffs (top 8)",
            "relegation_cut": None},
    "MLB": {"name": "MLB (baseball)", "grouped_by": "division",
            "size": 5, "window": (1995, 2021),
            "finals_cut": 1, "finals_label": "Division title (1st)",
            "relegation_cut": None},
    "EPL": {"name": "EPL (English football)", "grouped_by": "league",
            "size": 20, "window": (1996, 2025),
            "finals_cut": 4, "finals_label": "Champions League (top 4)",
            "relegation_cut": 18, "relegation_label": "Relegation (18-20)"},
    "AFL": {"name": "AFL (Australian rules)", "grouped_by": "league",
            "size": 18, "window": (2012, 2024),
            "finals_cut": 8, "finals_label": "Finals (top 8)",
            "relegation_cut": None},
    "NRL": {"name": "NRL (rugby league)", "grouped_by": "league",
            "size": 16, "window": (2007, 2022),
            "finals_cut": 8, "finals_label": "Finals (top 8)",
            "relegation_cut": None},
}

# ----- Helpers -------------------------------------------------------------
def rank_group(rows, key):
    """rows: list of dicts; key(row)->sortable tuple (higher=better).
    Returns list of (row, position) with 1 = best; ties share nothing here,
    positions are dense 1..n after a stable sort (ties broken by tiebreakers)."""
    ordered = sorted(rows, key=key, reverse=True)
    return [(r, i + 1) for i, r in enumerate(ordered)]

# =====================  NFL  ===============================================
NFL_CANON = {"OAK": "LV", "SD": "LAC", "STL": "LA"}  # relocations -> current
NFL_CONF = {
    # AFC
    "BUF":"AFC","MIA":"AFC","NE":"AFC","NYJ":"AFC",
    "BAL":"AFC","CIN":"AFC","CLE":"AFC","PIT":"AFC",
    "HOU":"AFC","IND":"AFC","JAX":"AFC","TEN":"AFC",
    "DEN":"AFC","KC":"AFC","LV":"AFC","LAC":"AFC",
    # NFC
    "DAL":"NFC","NYG":"NFC","PHI":"NFC","WAS":"NFC",
    "CHI":"NFC","DET":"NFC","GB":"NFC","MIN":"NFC",
    "ATL":"NFC","CAR":"NFC","NO":"NFC","TB":"NFC",
    "ARI":"NFC","LA":"NFC","SF":"NFC","SEA":"NFC",
}
def build_nfl():
    rec = defaultdict(lambda: {"w":0,"l":0,"t":0,"pd":0})  # (season,team)->
    with open(os.path.join(RAW,"nfl_games.csv")) as f:
        for r in csv.DictReader(f):
            if r["game_type"]!="REG": continue
            if not r["home_score"] or not r["away_score"]: continue
            s=int(r["season"])
            h=NFL_CANON.get(r["home_team"],r["home_team"])
            a=NFL_CANON.get(r["away_team"],r["away_team"])
            hs=int(r["home_score"]); as_=int(r["away_score"])
            for team,pf,pa in ((h,hs,as_),(a,as_,hs)):
                d=rec[(s,team)]; d["pd"]+=pf-pa
                if pf>pa: d["w"]+=1
                elif pf<pa: d["l"]+=1
                else: d["t"]+=1
    # group by season+conference
    by=defaultdict(list)
    for (s,team),d in rec.items():
        g=d["w"]+d["l"]+d["t"]
        wp=(d["w"]+0.5*d["t"])/g if g else 0
        conf=NFL_CONF[team]
        by[(s,conf)].append({"team":team,"wp":wp,"pd":d["pd"]})
    out=[]
    for (s,conf),rows in by.items():
        for row,pos in rank_group(rows, key=lambda x:(x["wp"],x["pd"])):
            out.append(("NFL",s,conf,row["team"],pos,len(rows),round(row["wp"],4)))
    return out

# =====================  NBA  ===============================================
NBA_CONF = {  # fran_id -> conference (stable 2005-2015)
    **{k:"East" for k in ["Bucks","Bulls","Cavaliers","Celtics","Hawks","Heat",
        "Hornets","Knicks","Magic","Nets","Pacers","Pistons","Raptors","Sixers","Wizards"]},
    **{k:"West" for k in ["Clippers","Grizzlies","Jazz","Kings","Lakers","Mavericks",
        "Nuggets","Pelicans","Rockets","Spurs","Suns","Thunder","Timberwolves",
        "Trailblazers","Warriors"]},
}
def build_nba():
    rec=defaultdict(lambda:{"w":0,"l":0,"pd":0})
    with open(os.path.join(RAW,"nba_allelo.csv")) as f:
        for r in csv.DictReader(f):
            if r["lg_id"]!="NBA" or r["is_playoffs"]!="0": continue
            s=int(r["year_id"])
            if not (2005<=s<=2015): continue  # window where NBA_CONF map is valid
            fr=r["fran_id"]
            pf=int(r["pts"]); pa=int(r["opp_pts"])
            d=rec[(s,fr)]; d["pd"]+=pf-pa
            if r["game_result"]=="W": d["w"]+=1
            else: d["l"]+=1
    by=defaultdict(list)
    for (s,fr),d in rec.items():
        g=d["w"]+d["l"]; wp=d["w"]/g if g else 0
        conf=NBA_CONF[fr]
        by[(s,conf)].append({"team":fr,"wp":wp,"pd":d["pd"]})
    out=[]
    for (s,conf),rows in by.items():
        for row,pos in rank_group(rows,key=lambda x:(x["wp"],x["pd"])):
            out.append(("NBA",s,conf,row["team"],pos,len(rows),round(row["wp"],4)))
    return out

# =====================  MLB  ===============================================
def build_mlb():
    out=[]
    by=defaultdict(list)
    with open(os.path.join(RAW,"mlb_teams.csv")) as f:
        for r in csv.DictReader(f):
            y=int(r["yearID"])
            if y<1995: continue
            if not r["divID"]: continue
            g=f'{r["lgID"]}-{r["divID"]}'
            by[(y,g)].append(r)
    for (y,g),rows in by.items():
        n=len(rows)
        for r in rows:
            out.append(("MLB",y,g,r["franchID"],int(r["Rank"]),n,
                        round(int(r["W"])/(int(r["W"])+int(r["L"])),4)))
    return out

# =====================  EPL  ===============================================
# Short forms used by openfootball vs full forms used by footballcsv -> canonical.
# Applied after stripping trailing " FC"/" AFC" so both sources map to one identity.
EPL_ALIASES={
    "Manchester Utd":"Manchester United", "Newcastle Utd":"Newcastle United",
    "Sheffield Utd":"Sheffield United", "Tottenham":"Tottenham Hotspur",
    "West Brom":"West Bromwich Albion", "West Ham":"West Ham United",
    "Wolves":"Wolverhampton Wanderers", "Brighton":"Brighton & Hove Albion",
}
def _norm_team(name):
    name=name.strip()
    name=re.sub(r"\s+(FC|AFC)$","",name).strip()
    return EPL_ALIASES.get(name,name)

def _epl_table(matches, season_end):
    tab=defaultdict(lambda:{"pts":0,"gf":0,"ga":0})
    for home,away,hg,ag in matches:
        th,ta=tab[home],tab[away]
        th["gf"]+=hg; th["ga"]+=ag; ta["gf"]+=ag; ta["ga"]+=hg
        if hg>ag: th["pts"]+=3
        elif hg<ag: ta["pts"]+=3
        else: th["pts"]+=1; ta["pts"]+=1
    rows=[{"team":t,"pts":d["pts"],"gd":d["gf"]-d["ga"],"gf":d["gf"]} for t,d in tab.items()]
    out=[]
    for row,pos in rank_group(rows,key=lambda x:(x["pts"],x["gd"],x["gf"])):
        out.append(("EPL",season_end,"ALL",row["team"],pos,len(rows),None))
    return out

DASH=r"[-–—]"  # ASCII hyphen, en-dash, em-dash all used across sources
# openfootball layout B (2024-25+): "Home  v  Away   H-G (ht)"  (score at end)
_of_b=re.compile(rf"^(?:\s*\d{{1,2}}:\d{{2}}\s+)?(.+?)\s+v\s+(.+?)\s+(\d+){DASH}(\d+)\s*(?:\({DASH}?\d+{DASH}\d+\))?\s*$")
# openfootball layout A (2021-24): "[time] Home  H-G (ht)  Away"  (score in middle)
_of_a=re.compile(rf"^(?:\s*\d{{1,2}}:\d{{2}}\s+)?(.+?)\s+(\d+){DASH}(\d+)\s*(?:\(\d+{DASH}\d+\))?\s+(.+?)\s*$")

def build_epl():
    out=[]
    # footballcsv seasons 1992-93 .. 2020-21 (FT score may use ASCII or en-dash)
    fdir=os.path.join(RAW,"epl_footballcsv")
    for fn in sorted(os.listdir(fdir)):
        if not fn.endswith(".csv"): continue
        start=int(fn.split("-")[0]); season_end=start+1
        matches=[]
        with open(os.path.join(fdir,fn)) as f:
            for r in csv.DictReader(f):
                ft=r.get("FT","").strip()
                m=re.match(rf"^(\d+){DASH}(\d+)$",ft)
                if not m: continue
                matches.append((_norm_team(r["Team 1"]),_norm_team(r["Team 2"]),
                                int(m.group(1)),int(m.group(2))))
        if matches: out+=_epl_table(matches,season_end)
    # openfootball .txt 2021-22 .. 2024-25 (two layouts, autodetect per line)
    odir=os.path.join(RAW,"epl_openfootball")
    for fn in sorted(os.listdir(odir)):
        if not fn.endswith(".txt"): continue
        start=int(fn.split("-")[0]); season_end=start+1
        matches=[]
        with open(os.path.join(odir,fn)) as f:
            for line in f:
                s=line.rstrip("\n")
                if not s.strip() or s.lstrip()[:1] in "#=▪": continue
                if re.search(rf"\d+{DASH}\d+", s) is None: continue
                if " v " in s:
                    m=_of_b.match(s)
                    if m: matches.append((_norm_team(m.group(1)),_norm_team(m.group(2)),
                                          int(m.group(3)),int(m.group(4))))
                else:
                    m=_of_a.match(s)
                    if m: matches.append((_norm_team(m.group(1)),int(m.group(2)),
                                          int(m.group(3)),_norm_team(m.group(4))))
                    # note: layout A groups are (home, hg, ag, away)
        # normalize tuple order for layout A entries handled above
        norm=[]
        for t in matches:
            if isinstance(t[1],int):  # layout A: (home,hg,ag,away)
                norm.append((t[0],t[3],t[1],t[2]))
            else:
                norm.append(t)
        if norm: out+=_epl_table(norm,season_end)
    return out

# =====================  AFL  ===============================================
def build_afl():
    out=[]
    by=defaultdict(lambda:defaultdict(lambda:{"pts":0,"pf":0,"pa":0}))
    with open(os.path.join(RAW,"afl_matches.csv")) as f:
        for r in csv.DictReader(f):
            if r["Round.Type"]!="Regular": continue
            s=int(r["Season"]); h=r["Home.Team"]; a=r["Away.Team"]
            hp=int(r["Home.Points"]); ap=int(r["Away.Points"])
            th,ta=by[s][h],by[s][a]
            th["pf"]+=hp; th["pa"]+=ap; ta["pf"]+=ap; ta["pa"]+=hp
            if hp>ap: th["pts"]+=4
            elif hp<ap: ta["pts"]+=4
            else: th["pts"]+=2; ta["pts"]+=2
    for s,teams in by.items():
        rows=[{"team":t,"pts":d["pts"],"pct":(100.0*d["pf"]/d["pa"] if d["pa"] else 0)}
              for t,d in teams.items()]
        for row,pos in rank_group(rows,key=lambda x:(x["pts"],x["pct"])):
            out.append(("AFL",s,"ALL",row["team"],pos,len(rows),None))
    return out

# =====================  NRL  ===============================================
def build_nrl():
    out=[]
    rows_by_year=defaultdict(list)
    with open(os.path.join(RAW,"nrl_ladder_round.csv")) as f:
        for r in csv.DictReader(f):
            if not r["competition_year"].startswith("NRL"): continue
            rows_by_year[int(r["year"])].append(r)
    for y,rows in rows_by_year.items():
        maxr=max(int(r["round"]) for r in rows)
        final=[r for r in rows if int(r["round"])==maxr]
        n=len(final)
        for r in final:
            out.append(("NRL",y,"ALL",r["team"],int(r["ladder_position"]),n,None))
    return out

# ----- Assemble ------------------------------------------------------------
BUILDERS={"NFL":build_nfl,"NBA":build_nba,"MLB":build_mlb,
          "EPL":build_epl,"AFL":build_afl,"NRL":build_nrl}

def main():
    long_rows=[]
    for lg,fn in BUILDERS.items():
        rows=fn()
        w0,w1=LEAGUE_META[lg]["window"]
        rows=[r for r in rows if w0<=r[1]<=w1]
        long_rows+=rows
        seasons=sorted({r[1] for r in rows})
        print(f"{lg}: {len(rows)} team-seasons, seasons {seasons[0]}-{seasons[-1]} "
              f"({len(seasons)} seasons)")

    with open(os.path.join(OUT,"standings_long.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["league","season","group","team","position","n_group","win_pct"])
        w.writerows(long_rows)

    # index: (league, team, group) -> {season: position}; also (league,team)->{season:(group,pos)}
    pos_idx=defaultdict(dict)   # (league,team) -> season -> (group,pos,n)
    for lg,s,g,team,pos,n,wp in long_rows:
        pos_idx[(lg,team)][s]=(g,pos,n)

    # transitions: consecutive seasons for same team
    trans=[]
    for (lg,team),bys in pos_idx.items():
        for s in sorted(bys):
            if s+1 in bys:
                g0,p0,n0=bys[s]; g1,p1,n1=bys[s+1]
                trans.append((lg,team,s,g0,p0,n0,s+1,g1,p1,n1,p1-p0))
    with open(os.path.join(OUT,"transitions.csv"),"w",newline="") as f:
        w=csv.writer(f)
        w.writerow(["league","team","season","group","pos","n_group",
                    "next_season","next_group","next_pos","next_n","movement"])
        w.writerows(trans)

    # aggregate box-plot stats per league per start position
    def quantile(sorted_vals,q):
        if not sorted_vals: return None
        if len(sorted_vals)==1: return float(sorted_vals[0])
        idx=q*(len(sorted_vals)-1); lo=int(idx); frac=idx-lo
        if lo+1<len(sorted_vals):
            return sorted_vals[lo]*(1-frac)+sorted_vals[lo+1]*frac
        return float(sorted_vals[lo])

    per=defaultdict(lambda:defaultdict(list))  # league -> start_pos -> [next_pos]
    for (lg,team,s,g0,p0,n0,s1,g1,p1,n1,mv) in trans:
        per[lg][p0].append(p1)

    # per-league persistence metrics: correlation & OLS slope of next_pos on pos.
    # Positions normalized to [0,1] via (pos-1)/(size-1) so slope is comparable
    # across leagues of different size. Pearson r is already scale-free.
    # r near 1 = consistent (finish order persists); r near 0 = strong
    # regression to the mean (this year's rank barely predicts next year's).
    def persistence(pairs, size):
        n=len(pairs)
        xs=[(p0-1)/(size-1) for p0,_ in pairs]
        ys=[(p1-1)/(size-1) for _,p1 in pairs]
        mx=sum(xs)/n; my=sum(ys)/n
        sxy=sum((x-mx)*(y-my) for x,y in zip(xs,ys))
        sxx=sum((x-mx)**2 for x in xs)
        syy=sum((y-my)**2 for y in ys)
        slope=sxy/sxx if sxx else 0.0
        r=sxy/((sxx*syy)**0.5) if sxx and syy else 0.0
        return {"n":n,"r":round(r,3),"slope":round(slope,3),"r2":round(r*r,3)}

    viz={"leagues":{}}
    for lg,meta in LEAGUE_META.items():
        positions=[]
        for p in sorted(per[lg]):
            vals=sorted(per[lg][p])
            positions.append({
                "pos":p, "n":len(vals),
                "min":vals[0], "q1":round(quantile(vals,0.25),2),
                "median":round(quantile(vals,0.5),2),
                "q3":round(quantile(vals,0.75),2), "max":vals[-1],
                "mean":round(statistics.fmean(vals),2),
                "mean_move":round(statistics.fmean([v-p for v in vals]),2),
                "values":vals,
            })
        viz["leagues"][lg]={
            "name":meta["name"], "grouped_by":meta["grouped_by"],
            "size":meta["size"], "window":meta["window"],
            "finals_cut":meta["finals_cut"], "finals_label":meta["finals_label"],
            "relegation_cut":meta.get("relegation_cut"),
            "relegation_label":meta.get("relegation_label"),
            "n_transitions":sum(len(per[lg][p]) for p in per[lg]),
            "persistence":persistence(
                [(p0,p1) for (l,tm,s,g0,pp0,n0,s1,g1,p1,n1,mv) in trans if l==lg
                 for p0 in [pp0]], meta["size"]),
            "positions":positions,
        }
    with open(os.path.join(OUT,"viz_data.json"),"w") as f:
        json.dump(viz,f,indent=1)
    print("\nWrote standings_long.csv, transitions.csv, viz_data.json")
    print(f"Total transitions: {len(trans)}")

if __name__=="__main__":
    main()
