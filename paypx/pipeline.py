"""End-to-end, rerunnable pipeline: scrape -> merge -> compute -> aggregate -> chart.

Parameterised by league and season so it can be reused for future transfer
windows or additional leagues (Phase 2: Serie A, Bundesliga, Ligue 1 — just add
them to config.LEAGUES).

Usage:
    python -m paypx.pipeline --leagues epl,laliga --season 2025-26
    python -m paypx.pipeline --leagues epl --formation both --backend playwright
    python -m paypx.pipeline --seed-only          # run only the 5 verified clubs
"""

from __future__ import annotations

import argparse
import json
import sys

import pandas as pd

from . import aggregate, build, charts, config


def _clubs_for(leagues: list[str], seed_only: bool) -> list[config.Club]:
    clubs: list[config.Club] = []
    for lg in leagues:
        for c in config.get_league(lg).clubs:
            if seed_only and c.key not in config.SEED_CLUBS:
                continue
            clubs.append(c)
    return clubs


def run(leagues, season, formation="actual", seed_only=False, verbose=True):
    """Run the pipeline; return (rows_df, {level: table}, report_dict)."""
    modes = ["actual", "forced433"] if formation == "both" else [formation]
    clubs = _clubs_for(leagues, seed_only)

    all_rows: list[dict] = []
    report = {"season": season, "leagues": leagues, "formation": formation,
              "clubs_built": [], "clubs_failed": {}, "unmatched": {}}

    for club in clubs:
        try:
            for mode in modes:
                result = build.build_club(club, season, formation=mode)
                all_rows.extend(build.rows_to_records(result))
                if mode == modes[0]:
                    report["clubs_built"].append(club.key)
                    if result.unmatched_lineup:
                        report["unmatched"][club.key] = result.unmatched_lineup
                    _write_club_interim(result)
                if verbose:
                    n = sum(1 for r in result.rows if r.matched)
                    print(f"  [{mode:9}] {club.key:18} "
                          f"median={result.median:,.0f} matched={n}/11")
        except Exception as exc:  # noqa: BLE001 - record, keep going
            report["clubs_failed"][club.key] = str(exc)
            if verbose:
                print(f"  [FAIL]      {club.key:18} {exc}", file=sys.stderr)

    df = pd.DataFrame(all_rows)
    # Aggregate on the actual-formation rows (primary result).
    actual = df[df["formation_mode"] == "actual"] if not df.empty else df
    tidy = aggregate.rows_to_frame(actual.to_dict("records")) \
        if not actual.empty else pd.DataFrame()
    tables = aggregate.league_tables(tidy) if not tidy.empty else {}

    _write_outputs(df, tables, tidy, season, report)
    return df, tables, report


def _write_club_interim(result: build.ClubResult) -> None:
    path = config.INTERIM / f"{result.club}_{result.formation}.json"
    path.write_text(json.dumps({
        "club": result.club, "league": result.league, "season": result.season,
        "formation": result.formation, "median": result.median,
        "rows": build.rows_to_records(result),
        "unmatched_lineup": result.unmatched_lineup,
        "unmatched_wage": result.unmatched_wage,
    }, indent=2), encoding="utf-8")


def _write_outputs(df, tables, tidy, season, report) -> None:
    if not df.empty:
        df.to_csv(config.OUTPUT / "starting_xi.csv", index=False)
    for level, table in tables.items():
        if table is not None and not table.empty:
            table.to_csv(config.OUTPUT / f"index_{level}.csv", index=False)
            charts.comparison_chart(table, level, season=season)
    # Sanity check vs the 5 validated clubs.
    if not tidy.empty:
        sc = aggregate.sanity_check(tidy, config.SEED_CLUBS)
        if not sc.empty:
            sc.to_csv(config.OUTPUT / "sanity_check.csv")
            report["sanity_check_clubs"] = list(sc.index)
    (config.OUTPUT / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Multi-league position pay index")
    ap.add_argument("--leagues", default="epl,laliga",
                    help="comma-separated league keys (default: epl,laliga)")
    ap.add_argument("--season", default=config.DEFAULT_SEASON)
    ap.add_argument("--formation", default="both",
                    choices=["actual", "forced433", "both"])
    ap.add_argument("--seed-only", action="store_true",
                    help="only build the 5 verified sanity-check clubs")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    leagues = [x.strip() for x in args.leagues.split(",") if x.strip()]
    print(f"paypx pipeline — leagues={leagues} season={args.season} "
          f"formation={args.formation} seed_only={args.seed_only}")
    df, tables, report = run(leagues, args.season, args.formation,
                             args.seed_only, verbose=not args.quiet)

    print("\n=== Broad index ===")
    if tables.get("broad") is not None and not tables["broad"].empty:
        print(tables["broad"].to_string(index=False))
    print("\n=== Granular index ===")
    if tables.get("granular") is not None and not tables["granular"].empty:
        print(tables["granular"].to_string(index=False))
    if report["clubs_failed"]:
        print(f"\n{len(report['clubs_failed'])} club(s) failed: "
              f"{list(report['clubs_failed'])}", file=sys.stderr)
    print(f"\nOutputs written to {config.OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
