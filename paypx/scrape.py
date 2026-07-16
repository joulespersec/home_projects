"""Fetch-and-cache raw HTML for wage and lineup sources.

Every fetch is cached to ``data/raw/{source}/{club_key}.html`` so reruns never
re-hit the network. Two fetch backends:

  * ``requests``  — default; fast, but blocked by Cloudflare-style anti-bot on
    salaryleaks/fbref/transfermarkt from datacenter IPs.
  * ``playwright`` — headless Chromium (preinstalled in this environment at
    /opt/pw-browsers). Slower, but can clear JS challenges. Enable with
    ``backend="playwright"`` or ``PAYPX_BACKEND=playwright``.

Nothing here fabricates data: if a fetch fails it raises, and the caller
records the club as un-scraped. Seed clubs bypass scraping entirely (see
``build.load_club``).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import requests

from . import config


class FetchError(RuntimeError):
    pass


def _cache_path(source: str, club_key: str) -> Path:
    d = config.RAW / source
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{club_key}.html"


def _fetch_requests(url: str) -> str:
    resp = requests.get(
        url,
        headers=config.REQUEST_HEADERS,
        timeout=config.REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        raise FetchError(f"HTTP {resp.status_code} for {url}")
    return resp.text


def _fetch_playwright(url: str) -> str:
    """Headless-Chromium fetch for anti-bot pages. Imported lazily."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - env dependent
        raise FetchError(
            "playwright not installed; `pip install playwright` "
            "(Chromium is preinstalled at /opt/pw-browsers)"
        ) from exc

    exe = os.environ.get("PAYPX_CHROMIUM", "/opt/pw-browsers/chromium")
    launch_kwargs: dict = {"headless": True}
    if Path(exe).exists():
        launch_kwargs["executable_path"] = exe
    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        try:
            page = browser.new_page(
                user_agent=config.REQUEST_HEADERS["User-Agent"]
            )
            page.goto(url, timeout=config.REQUEST_TIMEOUT * 1000,
                      wait_until="domcontentloaded")
            page.wait_for_timeout(2500)  # let any challenge/JS settle
            html = page.content()
        finally:
            browser.close()
    if "Just a moment" in html and len(html) < 4000:
        raise FetchError(f"anti-bot challenge not cleared for {url}")
    return html


def fetch(
    url: str,
    source: str,
    club_key: str,
    *,
    backend: str | None = None,
    force: bool = False,
) -> str:
    """Return page HTML, from cache when present.

    Set ``force=True`` to bypass the cache. ``backend`` overrides the
    ``PAYPX_BACKEND`` env var (default ``requests``).
    """
    cache = _cache_path(source, club_key)
    if cache.exists() and not force:
        return cache.read_text(encoding="utf-8")

    backend = backend or os.environ.get("PAYPX_BACKEND", "requests")
    fetcher = _fetch_playwright if backend == "playwright" else _fetch_requests

    html = fetcher(url)
    cache.write_text(html, encoding="utf-8")
    time.sleep(config.REQUEST_DELAY_SECONDS)  # be polite between live fetches
    return html


# --- URL builders ----------------------------------------------------------

def wage_url(club: config.Club) -> str:
    return f"{config.SALARYLEAKS_BASE}/{club.salaryleaks_slug}"


def fbref_url(club: config.Club) -> str:
    if not club.fbref_id:
        raise FetchError(f"no fbref_id registered for {club.key}")
    return f"{config.FBREF_BASE}/{club.fbref_id}/{club.fbref_slug}"


def transfermarkt_url(club: config.Club, season: str) -> str:
    # season "2025-26" -> transfermarkt season_id "2025"
    season_id = season.split("-")[0]
    slug = club.transfermarkt_slug or club.key
    tm_id = club.transfermarkt_id or ""
    return (
        f"{config.TRANSFERMARKT_BASE}/{slug}/startseite/verein/{tm_id}"
        f"/saison_id/{season_id}"
    )
