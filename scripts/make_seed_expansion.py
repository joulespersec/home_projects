"""Generate ESTIMATED seed data for additional clubs (curated expansion).

Lower confidence than the 5 validated clubs. Wage tiers are anchored to public
reporting (Capology/Spotrac/SalaryLeaks/press via web search, 2026-07-16);
per-player figures for non-headline players are reasoned estimates from squad
role/tier, and XIs are reconstructed most-used 2025-26 lineups. Every file
carries confidence="estimated" and is excluded from the validated sanity check.

This exists so league aggregates have real breadth to demonstrate; it is a
stopgap until the live scrape (`python -m paypx.pipeline`) supplies the
authoritative full 20-per-league dataset. Treat the tail figures as indicative.
"""

import json
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
SEED.mkdir(parents=True, exist_ok=True)

PROVENANCE = (
    "ESTIMATED curated data. Wage tiers anchored to public reporting "
    "(Capology/Spotrac/SalaryLeaks/press) via web search 2026-07-16; "
    "non-headline per-player wages reasoned from squad role/tier. XI = "
    "reconstructed most-used 2025-26 lineup. Indicative only — replace with a "
    "live scrape before any published claim."
)


def club(key, league, currency, xi, note=""):
    """xi: list of (name, granular, weekly). Minutes/starts synthesised high."""
    wages, lineup = [], []
    for i, (name, gran, weekly) in enumerate(xi):
        wages.append({"name": name, "weekly": weekly,
                      "annual": weekly * 52, "currency": currency})
        lineup.append({"name": name, "granular": gran,
                       "minutes": 2900 - i * 30, "starts": 32 - i})
    data = {
        "club": key, "league": league, "season": "2025-26",
        "currency": currency, "confidence": "estimated",
        "provenance": PROVENANCE, "formation_note": note,
        "wages": wages, "lineup": lineup,
    }
    (SEED / f"{key}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {key}.json (estimated)")


# ===== Premier League =====================================================

club("chelsea", "epl", "GBP", note="4-2-3-1 (Maresca)", xi=[
    ("Robert Sánchez", "GK", 75), ("Reece James", "FB", 200),
    ("Wesley Fofana", "CB", 200), ("Levi Colwill", "CB", 80),
    ("Marc Cucurella", "FB", 175), ("Moisés Caicedo", "DM", 200),
    ("Enzo Fernández", "CM", 180), ("Cole Palmer", "AM", 130),
    ("Pedro Neto", "W", 160), ("Estêvão", "W", 80), ("João Pedro", "ST", 90),
])

club("man-united", "epl", "GBP", note="3-4-2-1 (Amorim)", xi=[
    ("André Onana", "GK", 120), ("Matthijs de Ligt", "CB", 130),
    ("Leny Yoro", "CB", 85), ("Luke Shaw", "CB", 150),
    ("Noussair Mazraoui", "FB", 90), ("Patrick Dorgu", "FB", 40),
    ("Casemiro", "CM", 350), ("Bruno Fernandes", "CM", 300),
    ("Matheus Cunha", "AM", 90), ("Bryan Mbeumo", "AM", 120),
    ("Benjamin Šeško", "ST", 90),
])

club("tottenham", "epl", "GBP", note="4-2-3-1 (Frank)", xi=[
    ("Guglielmo Vicario", "GK", 80), ("Pedro Porro", "FB", 90),
    ("Cristian Romero", "CB", 195), ("Micky van de Ven", "CB", 90),
    ("Destiny Udogie", "FB", 70), ("João Palhinha", "DM", 135),
    ("Rodrigo Bentancur", "CM", 90), ("Xavi Simons", "AM", 195),
    ("Mohammed Kudus", "W", 150), ("Brennan Johnson", "W", 80),
    ("Dominic Solanke", "ST", 110),
])

club("newcastle", "epl", "GBP", note="4-3-3 (Howe)", xi=[
    ("Nick Pope", "GK", 60), ("Tino Livramento", "FB", 50),
    ("Sven Botman", "CB", 70), ("Fabian Schär", "CB", 60),
    ("Lewis Hall", "FB", 45), ("Sandro Tonali", "DM", 120),
    ("Bruno Guimarães", "CM", 160), ("Joelinton", "CM", 150),
    ("Harvey Barnes", "W", 60), ("Anthony Gordon", "W", 150),
    ("Nick Woltemade", "ST", 80),
])

club("aston-villa", "epl", "GBP", note="4-2-3-1 (Emery)", xi=[
    ("Emiliano Martínez", "GK", 150), ("Matty Cash", "FB", 55),
    ("Ezri Konsa", "CB", 70), ("Pau Torres", "CB", 65),
    ("Lucas Digne", "FB", 55), ("Boubacar Kamara", "DM", 150),
    ("Youri Tielemans", "CM", 150), ("Morgan Rogers", "AM", 150),
    ("Leon Bailey", "W", 65), ("Jadon Sancho", "W", 200),
    ("Ollie Watkins", "ST", 130),
])

# ===== La Liga =============================================================

club("atletico-madrid", "laliga", "EUR", note="4-2-3-1 (Simeone)", xi=[
    ("Jan Oblak", "GK", 375), ("Nahuel Molina", "FB", 90),
    ("José María Giménez", "CB", 110), ("Robin Le Normand", "CB", 100),
    ("David Hancko", "FB", 80), ("Koke", "DM", 130),
    ("Pablo Barrios", "CM", 60), ("Antoine Griezmann", "AM", 180),
    ("Nico González", "W", 90), ("Giuliano Simeone", "W", 45),
    ("Julián Álvarez", "ST", 240),
])

club("athletic-club", "laliga", "EUR", note="4-2-3-1 (Valverde)", xi=[
    ("Unai Simón", "GK", 96), ("Andoni Gorosabel", "FB", 40),
    ("Aymeric Laporte", "CB", 173), ("Dani Vivian", "CB", 70),
    ("Yuri Berchiche", "FB", 50), ("Mikel Vesga", "DM", 40),
    ("Iñigo Ruiz de Galarreta", "CM", 45), ("Oihan Sancet", "AM", 80),
    ("Nico Williams", "W", 250), ("Iñaki Williams", "W", 219),
    ("Gorka Guruzeta", "ST", 45),
])

club("real-sociedad", "laliga", "EUR", note="4-3-3", xi=[
    ("Álex Remiro", "GK", 90), ("Hamari Traoré", "FB", 45),
    ("Igor Zubeldia", "CB", 70), ("Nayef Aguerd", "CB", 55),
    ("Aihen Muñoz", "FB", 40), ("Beñat Turrientes", "DM", 30),
    ("Brais Méndez", "CM", 80), ("Luka Sučić", "CM", 55),
    ("Ander Barrenetxea", "W", 45), ("Takefusa Kubo", "W", 90),
    ("Mikel Oyarzabal", "ST", 120),
])

club("villarreal", "laliga", "EUR", note="4-3-3 (Marcelino)", xi=[
    ("Luiz Júnior", "GK", 40), ("Juan Foyth", "FB", 77),
    ("Logan Costa", "CB", 40), ("Rafa Marín", "CB", 45),
    ("Alfonso Pedraza", "FB", 64), ("Santi Comesaña", "DM", 40),
    ("Dani Parejo", "CM", 60), ("Thomas Partey", "CM", 70),
    ("Yeremy Pino", "W", 55), ("Nicolas Pepe", "W", 67),
    ("Georges Mikautadze", "ST", 88),
])

club("real-betis", "laliga", "EUR", note="4-2-3-1 (Pellegrini)", xi=[
    ("Pau López", "GK", 55), ("Héctor Bellerín", "FB", 60),
    ("Marc Bartra", "CB", 45), ("Natan", "CB", 50),
    ("Junior Firpo", "FB", 45), ("Sofyan Amrabat", "DM", 90),
    ("Marc Roca", "CM", 45), ("Isco", "AM", 115),
    ("Abde Ezzalzouli", "W", 55), ("Antony", "W", 120),
    ("Cucho Hernández", "ST", 70),
])

club("sevilla", "laliga", "EUR", note="4-3-3 (Almeyda)", xi=[
    ("Ørjan Nyland", "GK", 30), ("Juanlu Sánchez", "FB", 25),
    ("Marcão", "CB", 80), ("Kike Salas", "CB", 30),
    ("Adrià Pedrosa", "FB", 35), ("Djibril Sow", "DM", 55),
    ("Lucien Agoumé", "CM", 40), ("Saúl Ñíguez", "CM", 60),
    ("Alexis Sánchez", "W", 50), ("Rubén Vargas", "W", 70),
    ("Isaac Romero", "ST", 30),
])

print("done — expansion seed files in", SEED)
