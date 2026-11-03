"""Small HTTP API that returns a GitHub user's public gists.

GET /<user>                 -> list of the user's public gists
GET /<user>?page=2&per_page=10  -> optional pagination, passed through to GitHub
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

GITHUB_API = os.environ.get("GITHUB_API_URL", "https://api.github.com")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # optional, raises the rate limit
PORT = int(os.environ.get("PORT", "8080"))
TIMEOUT = 10

# GitHub usernames: alphanumeric or single hyphens, max 39 chars.
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}$")


class UpstreamError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def fetch_gists(user, page=None, per_page=None):
    """Call the GitHub API and return a trimmed list of gists."""
    params = {k: v for k, v in (("page", page), ("per_page", per_page)) if v}
    url = f"{GITHUB_API}/users/{urllib.parse.quote(user)}/gists"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gists-api",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise UpstreamError(HTTPStatus.NOT_FOUND, f"user '{user}' not found")
        if e.code == 429 or (e.code == 403 and e.headers.get("X-RateLimit-Remaining") == "0"):
            raise UpstreamError(HTTPStatus.TOO_MANY_REQUESTS, "GitHub rate limit reached")
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, f"GitHub returned {e.code}")
    except (urllib.error.URLError, TimeoutError) as e:
        raise UpstreamError(HTTPStatus.BAD_GATEWAY, f"could not reach GitHub: {e}")

    return [
        {
            "id": g.get("id"),
            "description": g.get("description"),
            "url": g.get("html_url"),
            "files": list((g.get("files") or {}).keys()),
            "created_at": g.get("created_at"),
            "updated_at": g.get("updated_at"),
        }
        for g in data
    ]


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        payload = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        user = parsed.path.strip("/")

        if not user:
            return self._send(HTTPStatus.OK, {"usage": "GET /<github-username>"})
        if not USERNAME_RE.match(user):
            return self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid username"})

        query = urllib.parse.parse_qs(parsed.query)
        page = query.get("page", [None])[0]
        per_page = query.get("per_page", [None])[0]
        for name, value in (("page", page), ("per_page", per_page)):
            if value is not None and not value.isdigit():
                return self._send(HTTPStatus.BAD_REQUEST, {"error": f"{name} must be a positive integer"})

        try:
            gists = fetch_gists(user, page, per_page)
        except UpstreamError as e:
            return self._send(e.status, {"error": e.message})

        self._send(HTTPStatus.OK, {"user": user, "count": len(gists), "gists": gists})


def make_server(port=PORT):
    return ThreadingHTTPServer(("0.0.0.0", port), Handler)


if __name__ == "__main__":
    server = make_server()
    print(f"Listening on :{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
