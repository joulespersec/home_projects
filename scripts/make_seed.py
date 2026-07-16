"""Generate curated seed data for the 5 sanity-check clubs.

IMPORTANT — provenance: these are CURATED ESTIMATES assembled from public wage
reporting (Capology / Spotrac / SalaryLeaks / press) gathered via web search on
2026-07-16, NOT a live scrape. Wages are journalist-estimated weekly base
figures; XIs are a reconstructed most-used 2025-26 lineup. They exist to prove
the pipeline end-to-end and give an approximate sanity check. Replace with a
live scrape (`python -m paypx.pipeline`) before treating any number as final.

Name spellings deliberately differ between the wage list and the lineup list
(accents, nicknames, suffixes) so the name-matching stage is genuinely exercised.
Bench players (lower minutes) are included so XI selection has a real pool.
"""

import json
from pathlib import Path

SEED = Path(__file__).resolve().parent.parent / "data" / "seed"
SEED.mkdir(parents=True, exist_ok=True)

PROVENANCE = (
    "Curated estimate from public wage reporting (Capology/Spotrac/SalaryLeaks/"
    "press) gathered via web search 2026-07-16; NOT a live scrape. Weekly base "
    "wages, journalist-estimated. XI = reconstructed most-used 2025-26 lineup. "
    "Approximate — verify against a live scrape before publication."
)


def club(key, league, currency, xi, bench, formation_note=""):
    """xi/bench: list of (lineup_name, wage_name, granular, weekly, min, starts)."""
    wages, lineup = [], []
    for lname, wname, gran, weekly, mins, starts in xi + bench:
        wages.append({"name": wname, "weekly": weekly,
                      "annual": weekly * 52, "currency": currency})
        lineup.append({"name": lname, "granular": gran,
                       "minutes": mins, "starts": starts})
    data = {
        "club": key, "league": league, "season": "2025-26",
        "currency": currency, "provenance": PROVENANCE,
        "formation_note": formation_note,
        "wages": wages, "lineup": lineup,
    }
    (SEED / f"{key}.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {key}.json  ({len(xi)} XI + {len(bench)} bench)")


# (lineup_name, wage_name, granular, weekly_wage, minutes, starts)
# -- Manchester City (GBP, ~4-2-3-1) ---------------------------------------
club("man-city", "epl", "GBP",
     xi=[
         ("Gianluigi Donnarumma", "Gianluigi Donnarumma", "GK", 250, 3100, 34),
         ("Matheus Nunes", "Matheus Nunes", "FB", 110, 2400, 27),
         ("Rúben Dias", "Ruben Dias", "CB", 220, 3000, 33),
         ("Joško Gvardiol", "Josko Gvardiol", "CB", 130, 2900, 32),
         ("Nathan Aké", "Nathan Ake", "FB", 120, 2100, 23),
         ("Rodri", "Rodrigo Hernandez", "DM", 220, 2600, 29),
         ("Tijjani Reijnders", "Tijjani Reijnders", "CM", 140, 2700, 30),
         ("Bernardo Silva", "Bernardo Silva", "CM", 160, 2500, 28),
         ("Savinho", "Savinho", "W", 70, 2300, 25),
         ("Phil Foden", "Phil Foden", "W", 150, 2600, 29),
         ("Erling Haaland", "Erling Haaland", "ST", 525, 3000, 33),
     ],
     bench=[
         ("Rayan Cherki", "Rayan Cherki", "AM", 180, 1200, 10),
         ("Omar Marmoush", "Omar Marmoush", "ST", 120, 1400, 13),
         ("Nico González", "Nico Gonzalez", "DM", 90, 1300, 12),
         ("Abdukodir Khusanov", "Abdukodir Khusanov", "CB", 40, 900, 8),
     ],
     formation_note="4-2-3-1; Rodri single pivot when fit.")

# -- Liverpool (GBP, ~4-2-3-1) ---------------------------------------------
club("liverpool", "epl", "GBP",
     xi=[
         ("Alisson", "Alisson Becker", "GK", 150, 2800, 31),
         ("Jeremie Frimpong", "Jeremie Frimpong", "FB", 85, 2200, 24),
         ("Virgil van Dijk", "Virgil van Dijk", "CB", 350, 3200, 35),
         ("Ibrahima Konaté", "Ibrahima Konate", "CB", 120, 2600, 29),
         ("Milos Kerkez", "Milos Kerkez", "FB", 70, 2400, 27),
         ("Ryan Gravenberch", "Ryan Gravenberch", "DM", 80, 2900, 32),
         ("Alexis Mac Allister", "Alexis Mac Allister", "CM", 150, 2700, 30),
         ("Florian Wirtz", "Florian Wirtz", "AM", 195, 2500, 28),
         ("Mohamed Salah", "Mohamed Salah", "W", 400, 3100, 34),
         ("Cody Gakpo", "Cody Gakpo", "W", 120, 2400, 27),
         ("Alexander Isak", "Alexander Isak", "ST", 280, 2600, 28),
     ],
     bench=[
         ("Dominik Szoboszlai", "Dominik Szoboszlai", "CM", 120, 1900, 20),
         ("Hugo Ekitike", "Hugo Ekitike", "ST", 110, 1500, 14),
         ("Conor Bradley", "Conor Bradley", "FB", 40, 1200, 11),
     ],
     formation_note="4-2-3-1; Wirtz at 10, Gravenberch anchor.")

# -- Arsenal (GBP, ~4-3-3) --------------------------------------------------
club("arsenal", "epl", "GBP",
     xi=[
         ("David Raya", "David Raya", "GK", 100, 3200, 35),
         ("Jurriën Timber", "Jurrien Timber", "FB", 75, 2600, 29),
         ("William Saliba", "William Saliba", "CB", 250, 3000, 33),
         ("Gabriel Magalhães", "Gabriel", "CB", 120, 2900, 32),
         ("Riccardo Calafiori", "Riccardo Calafiori", "FB", 70, 2200, 24),
         ("Martín Zubimendi", "Martin Zubimendi", "DM", 130, 2800, 31),
         ("Declan Rice", "Declan Rice", "CM", 240, 3000, 33),
         ("Martin Ødegaard", "Martin Odegaard", "AM", 240, 2700, 30),
         ("Bukayo Saka", "Bukayo Saka", "W", 300, 2800, 31),
         ("Gabriel Martinelli", "Gabriel Martinelli", "W", 90, 2200, 24),
         ("Viktor Gyökeres", "Viktor Gyokeres", "ST", 150, 2600, 29),
     ],
     bench=[
         ("Kai Havertz", "Kai Havertz", "ST", 280, 1400, 13),
         ("Eberechi Eze", "Eberechi Eze", "AM", 190, 1700, 16),
         ("Noni Madueke", "Noni Madueke", "W", 90, 1300, 12),
     ],
     formation_note="4-3-3; Zubimendi 6, Rice/Ødegaard 8s.")

# -- Real Madrid (EUR, ~4-2-3-1) -------------------------------------------
club("real-madrid", "laliga", "EUR",
     xi=[
         ("Thibaut Courtois", "Thibaut Courtois", "GK", 250, 3000, 33),
         ("Trent Alexander-Arnold", "Trent Alexander-Arnold", "FB", 240, 2300, 25),
         ("Éder Militão", "Eder Militao", "CB", 150, 2400, 26),
         ("Antonio Rüdiger", "Antonio Rudiger", "CB", 190, 2600, 28),
         ("Álvaro Carreras", "Alvaro Carreras", "FB", 90, 2500, 27),
         ("Aurélien Tchouaméni", "Aurelien Tchouameni", "DM", 190, 2800, 31),
         ("Federico Valverde", "Fede Valverde", "CM", 320, 3100, 34),
         ("Jude Bellingham", "Jude Bellingham", "AM", 400, 2700, 30),
         ("Vinícius Júnior", "Vinicius Jr", "W", 480, 2900, 31),
         ("Rodrygo", "Rodrygo", "W", 190, 2200, 24),
         ("Kylian Mbappé", "Kylian Mbappe", "ST", 600, 3100, 34),
     ],
     bench=[
         ("Arda Güler", "Arda Guler", "AM", 90, 1600, 15),
         ("Dean Huijsen", "Dean Huijsen", "CB", 90, 1800, 18),
         ("Eduardo Camavinga", "Eduardo Camavinga", "CM", 150, 1500, 14),
     ],
     formation_note="4-2-3-1 under Xabi Alonso; Bellingham at 10.")

# -- Barcelona (EUR, ~4-3-3) ------------------------------------------------
club("barcelona", "laliga", "EUR",
     xi=[
         ("Marc-André ter Stegen", "Marc-Andre ter Stegen", "GK", 320, 2400, 26),
         ("Jules Koundé", "Jules Kounde", "FB", 120, 3000, 33),
         ("Pau Cubarsí", "Pau Cubarsi", "CB", 40, 2900, 32),
         ("Ronald Araújo", "Ronald Araujo", "CB", 100, 2500, 27),
         ("Alejandro Balde", "Alejandro Balde", "FB", 80, 2600, 28),
         ("Marc Casadó", "Marc Casado", "DM", 30, 2100, 22),
         ("Frenkie de Jong", "Frenkie de Jong", "CM", 140, 2900, 32),
         ("Pedri", "Pedri", "CM", 240, 3000, 33),
         ("Lamine Yamal", "Lamine Yamal", "W", 320, 2900, 32),
         ("Raphinha", "Raphinha", "W", 280, 2800, 31),
         ("Robert Lewandowski", "Robert Lewandowski", "ST", 600, 2400, 26),
     ],
     bench=[
         ("Dani Olmo", "Dani Olmo", "AM", 150, 1700, 16),
         ("Ferran Torres", "Ferran Torres", "ST", 90, 1600, 15),
         ("Marcus Rashford", "Marcus Rashford", "W", 150, 1500, 14),
     ],
     formation_note="4-3-3 under Flick; Casadó/De Jong pivot, Pedri LCM.")

print("done — seed files in", SEED)
