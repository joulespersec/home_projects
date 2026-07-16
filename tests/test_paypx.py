"""Unit tests for the core pipeline logic (no network required)."""

import statistics

import pytest

from paypx import aggregate, build, config, names, parse, positions


# --- positions -------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("GK", "GK"), ("Goalkeeper", "GK"),
    ("DF", "CB"), ("CB", "CB"), ("RB", "FB"), ("LWB", "FB"),
    ("DM", "DM"), ("CDM", "DM"), ("MF", "CM"), ("CM", "CM"),
    ("AM", "AM"), ("CAM", "AM"), ("RW", "W"), ("LW", "W"), ("Winger", "W"),
    ("ST", "ST"), ("CF", "ST"), ("FW", "ST"),
    ("DF,MF", "CB"),          # fbref compound -> first token
    ("CB/RB", "CB"),
])
def test_to_granular(raw, expected):
    assert positions.to_granular(raw) == expected


def test_to_granular_unknown_returns_none():
    assert positions.to_granular("zzz") is None
    assert positions.to_granular("") is None
    assert positions.to_granular(None) is None


@pytest.mark.parametrize("granular,broad", [
    ("GK", "GK"), ("CB", "DEF"), ("FB", "DEF"),
    ("DM", "MID"), ("CM", "MID"), ("AM", "MID"),
    ("W", "FWD"), ("ST", "FWD"),
])
def test_rollup(granular, broad):
    assert positions.GRANULAR_TO_BROAD[granular] == broad
    assert positions.to_broad(granular) == broad


def test_winger_rolls_up_to_fwd_not_mid():
    # The key convention decision from the brief.
    assert positions.to_broad("RW") == "FWD"
    assert positions.to_broad("CAM") == "MID"


# --- names -----------------------------------------------------------------

def test_strip_accents():
    assert names.strip_accents("Nuñez") == "Nunez"
    assert names.strip_accents("Ødegaard").endswith("degaard")


@pytest.mark.parametrize("a,b", [
    ("Martin Ødegaard", "Martin Odegaard"),
    ("Vinícius Júnior", "Vinicius Jr"),
    ("Rúben Dias", "Ruben Dias"),
    ("Joško Gvardiol", "Josko Gvardiol"),
])
def test_normalize_equivalence(a, b):
    assert names.normalize(a) == names.normalize(b)


def test_match_mononym_to_fullname():
    res = names.match_names(["Alisson"], ["Alisson Becker", "Mohamed Salah"])
    assert res.pairs["Alisson"] == "Alisson Becker"
    assert not res.unmatched_lineup


def test_match_reports_unmatched():
    res = names.match_names(["Nobody Here"], ["Someone Else"])
    assert res.unmatched_lineup == ["Nobody Here"]
    assert res.unmatched_wage == ["Someone Else"]


def test_match_wage_used_once():
    # Two lineup names must not both grab the same wage row.
    res = names.match_names(
        ["Gabriel Magalhães", "Gabriel Jesus"],
        ["Gabriel", "Gabriel Jesus"],
    )
    assert len(set(res.pairs.values())) == len(res.pairs)


# --- money parsing ---------------------------------------------------------

@pytest.mark.parametrize("text,amount", [
    ("£325,000", 325_000),
    ("€27.3m", 27_300_000),
    ("$180K", 180_000),
    ("19.5 M", 19_500_000),
    ("250000", 250_000),
])
def test_parse_money(text, amount):
    val, _ = parse.parse_money(text)
    assert val == amount


def test_parse_money_currency():
    assert parse.parse_money("£100")[1] == "GBP"
    assert parse.parse_money("€100")[1] == "EUR"


# --- build / index ---------------------------------------------------------

def test_index_is_salary_over_median():
    club = config.get_club("man-city")
    res = build.build_club(club, "2025-26", formation="actual")
    salaries = [r.annual for r in res.rows if r.matched]
    assert res.median == statistics.median(salaries)
    for r in res.rows:
        if r.matched and res.median:
            assert r.index == pytest.approx(r.annual / res.median, abs=1e-4)
    # Median player indexes to ~1.00 by construction.
    idx = sorted(r.index for r in res.rows if r.index is not None)
    assert statistics.median(idx) == pytest.approx(1.0, abs=1e-4)


def test_all_seed_clubs_build_full_xi():
    for key in config.SEED_CLUBS:
        res = build.build_club(config.get_club(key), "2025-26")
        assert len(res.rows) == 11
        matched = [r for r in res.rows if r.matched]
        assert len(matched) == 11, f"{key}: {res.unmatched_lineup}"


def test_forced_433_has_standard_shape():
    res = build.build_club(config.get_club("man-city"), "2025-26",
                           formation="forced433")
    slots = [r.granular for r in res.rows]
    assert sorted(slots) == sorted(positions.FORCED_433)


# --- aggregate -------------------------------------------------------------

def test_aggregate_flags_high_spread():
    rows = []
    for key in config.SEED_CLUBS:
        res = build.build_club(config.get_club(key), "2025-26")
        rows.extend(build.rows_to_records(res))
    df = aggregate.rows_to_frame(rows)
    broad = aggregate.aggregate(df, "broad")
    assert set(broad["league"]) == {"epl", "laliga"}
    assert "high_spread" in broad
    # Strikers should out-earn the median everywhere.
    gran = aggregate.aggregate(df, "granular")
    st = gran[gran["position"] == "ST"]
    assert (st["mean_index"] > 1.5).all()
