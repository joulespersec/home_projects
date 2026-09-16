"""
Spotify Authorization Code flow for local personal use.
Run once to authorize; later scripts refresh the token automatically.

Note: as of the Feb 2026 Spotify API changes, Development Mode requires
the app owner's account to have Premium, and the Client Credentials flow
no longer covers metadata endpoints. This uses the full Authorization
Code flow (user login), which those changes don't affect.
"""
import os
import json
import time
import base64
import webbrowser
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
SCOPE = "user-top-read"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".spotify_token.json")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

_auth_code = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _auth_code["code"] = params.get("code", [None])[0]
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body>Authorized. You can close this tab.</body></html>")

    def log_message(self, *args):
        pass  # silence default request logging


def _authorize():
    parsed = urllib.parse.urlparse(REDIRECT_URI)
    port = parsed.port or 8888

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
    }
    webbrowser.open(f"{AUTH_URL}?{urllib.parse.urlencode(params)}")

    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.handle_request()  # blocks until the redirect hits

    code = _auth_code.get("code")
    if not code:
        raise RuntimeError("Authorization failed -- no code received.")

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {auth_header}"},
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    resp.raise_for_status()
    token = resp.json()
    token["obtained_at"] = time.time()
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f)
    return token


def _refresh(token):
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    resp = requests.post(
        TOKEN_URL,
        headers={"Authorization": f"Basic {auth_header}"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        },
    )
    resp.raise_for_status()
    new_token = resp.json()
    new_token.setdefault("refresh_token", token["refresh_token"])
    new_token["obtained_at"] = time.time()
    with open(TOKEN_FILE, "w") as f:
        json.dump(new_token, f)
    return new_token


def get_access_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            token = json.load(f)
        if time.time() < token["obtained_at"] + token["expires_in"] - 60:
            return token["access_token"]
        token = _refresh(token)
        return token["access_token"]
    token = _authorize()
    return token["access_token"]


if __name__ == "__main__":
    print("Access token acquired:", get_access_token()[:12] + "...")
