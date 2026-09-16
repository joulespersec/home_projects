"""
Thin Last.fm API client for the complement engine.

Auth is just an API key (get one at https://www.last.fm/api/account/create);
the read methods we use need no user session. Last.fm returns HTTP 200 even
for logical errors, carrying an {"error", "message"} body instead, so we check
for that explicitly.
"""
import os
import time

import requests

BASE_URL = "https://ws.audioscrobbler.com/2.0/"
DEFAULT_USER_AGENT = "VinylTracker/0.1 +https://github.com/joulespersec/home_projects"

# Last.fm asks for reasonable use; ~4 req/sec is polite.
DEFAULT_MIN_INTERVAL = 0.25
MAX_RETRIES = 4


class LastfmError(RuntimeError):
    pass


class LastfmClient:
    def __init__(self, api_key=None, user_agent=None, min_interval=DEFAULT_MIN_INTERVAL):
        self.api_key = api_key or os.environ.get("LASTFM_API_KEY")
        if not self.api_key:
            raise LastfmError(
                "No Last.fm API key. Set LASTFM_API_KEY in .env "
                "(create one at https://www.last.fm/api/account/create)."
            )
        self.min_interval = min_interval
        self._last_request = 0.0
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": user_agent or os.environ.get("LASTFM_USER_AGENT", DEFAULT_USER_AGENT)}
        )

    def _throttle(self):
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _get(self, params):
        params = {**params, "api_key": self.api_key, "format": "json"}
        for attempt in range(MAX_RETRIES):
            self._throttle()
            resp = self._session.get(BASE_URL, params=params, timeout=30)
            self._last_request = time.monotonic()

            if resp.status_code == 429:
                time.sleep(float(resp.headers.get("Retry-After", 2 ** attempt)))
                continue
            if 500 <= resp.status_code < 600:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code != 200:
                raise LastfmError(f"Last.fm -> {resp.status_code}: {resp.text[:200]}")

            data = resp.json()
            if isinstance(data, dict) and "error" in data:
                # 29 = rate limit exceeded; back off and retry.
                if data.get("error") == 29:
                    time.sleep(2 ** attempt)
                    continue
                raise LastfmError(f"Last.fm error {data.get('error')}: {data.get('message')}")
            return data

        raise LastfmError(f"Last.fm request failed after {MAX_RETRIES} attempts: {params.get('method')}")

    def similar_artists(self, artist, limit=50, autocorrect=True):
        """Return a list of {name, match, mbid, url} similar to `artist`."""
        data = self._get(
            {
                "method": "artist.getSimilar",
                "artist": artist,
                "limit": limit,
                "autocorrect": 1 if autocorrect else 0,
            }
        )
        artists = (data.get("similarartists", {}) or {}).get("artist", []) or []
        return [
            {
                "name": a.get("name"),
                "match": a.get("match"),
                "mbid": a.get("mbid") or None,
                "url": a.get("url") or None,
            }
            for a in artists
        ]
