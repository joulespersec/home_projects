"""
Thin Discogs API client for personal use.

Auth: a Discogs personal access token (Settings -> Developers) sent as
`Authorization: Discogs token=<token>`. Discogs also *requires* a descriptive
User-Agent or it returns 403, so one is always set.

Rate limits: authenticated requests get 60/min. We pace requests to stay under
that and honour `Retry-After` on 429 rather than hammering.
"""
import os
import time

import requests

BASE_URL = "https://api.discogs.com"
DEFAULT_USER_AGENT = "VinylTracker/0.1 +https://github.com/joulespersec/home_projects"

# 60 req/min authenticated -> ~1s spacing keeps us comfortably under.
DEFAULT_MIN_INTERVAL = 1.1
MAX_RETRIES = 4


class DiscogsError(RuntimeError):
    pass


class DiscogsClient:
    def __init__(self, token=None, user_agent=None, min_interval=DEFAULT_MIN_INTERVAL):
        self.token = token or os.environ.get("DISCOGS_TOKEN")
        if not self.token:
            raise DiscogsError(
                "No Discogs token. Set DISCOGS_TOKEN in .env "
                "(Discogs -> Settings -> Developers -> generate token)."
            )
        self.user_agent = user_agent or os.environ.get("DISCOGS_USER_AGENT", DEFAULT_USER_AGENT)
        self.min_interval = min_interval
        self._last_request = 0.0
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Discogs token={self.token}",
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            }
        )

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _get(self, path, params=None):
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        for attempt in range(MAX_RETRIES):
            self._throttle()
            resp = self._session.get(url, params=params, timeout=30)
            self._last_request = time.monotonic()

            if resp.status_code == 429:
                wait = float(resp.headers.get("Retry-After", 2 ** attempt))
                time.sleep(max(wait, 1.0))
                continue
            if 500 <= resp.status_code < 600:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code != 200:
                raise DiscogsError(f"GET {url} -> {resp.status_code}: {resp.text[:200]}")
            return resp.json()

        raise DiscogsError(f"GET {url} failed after {MAX_RETRIES} attempts")

    def search_artist(self, name):
        """Return the raw list of `type=artist` search results for `name`."""
        data = self._get("/database/search", {"q": name, "type": "artist", "per_page": 20})
        return data.get("results", [])

    def artist_releases(self, artist_id, per_page=100):
        """
        Yield every item from an artist's releases, following pagination.
        Items include masters and releases with a `role` ('Main', 'Appearance',
        ...), `type`, `title`, `year`, `id`, `thumb`, `resource_url`.
        """
        url = f"/artists/{artist_id}/releases"
        params = {"per_page": per_page, "sort": "year", "sort_order": "desc"}
        while True:
            data = self._get(url, params)
            for item in data.get("releases", []):
                yield item
            nxt = (data.get("pagination", {}).get("urls", {}) or {}).get("next")
            if not nxt:
                break
            url, params = nxt, None  # `next` is a fully-formed URL

    def search_master_stats(self, artist_name, per_page=100):
        """
        One (paginated) `type=master` search for an artist, returning a map of
        {master_id: {have, want, formats}} harvested from the community stats
        Discogs bundles into search results. Used to enrich the authoritative
        release list without a per-record lookup.
        """
        stats = {}
        params = {"artist": artist_name, "type": "master", "per_page": per_page}
        url = "/database/search"
        while True:
            data = self._get(url, params)
            for result in data.get("results", []):
                master_id = result.get("master_id") or result.get("id")
                if master_id is None:
                    continue
                community = result.get("community", {}) or {}
                stats[int(master_id)] = {
                    "have": community.get("have"),
                    "want": community.get("want"),
                    "formats": ",".join(result.get("format", []) or []),
                }
            nxt = (data.get("pagination", {}).get("urls", {}) or {}).get("next")
            if not nxt:
                break
            url, params = nxt, None
        return stats
