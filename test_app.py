import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from unittest import mock

import app


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=15) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


class ServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.make_server(port=0)  # random free port
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()


class TestGistsApi(ServerTestCase):
    """Unit tests - the GitHub call is mocked so these run offline."""

    SAMPLE = [{
        "id": "abc123",
        "description": "hello world",
        "html_url": "https://gist.github.com/octocat/abc123",
        "files": {"hello.py": {}},
        "created_at": "2020-01-01T00:00:00Z",
        "updated_at": "2020-01-02T00:00:00Z",
    }]

    def _mock_urlopen(self, data):
        resp = mock.MagicMock()
        resp.__enter__.return_value = resp
        resp.read.return_value = json.dumps(data).encode()
        return mock.patch("app.urllib.request.urlopen", side_effect=[resp])

    def test_lists_gists(self):
        with mock.patch("app.fetch_gists") as fetch:
            fetch.return_value = [{"id": "abc123", "files": ["hello.py"]}]
            status, body = get(self.base, "/octocat")
        self.assertEqual(status, 200)
        self.assertEqual(body["user"], "octocat")
        self.assertEqual(body["count"], 1)
        fetch.assert_called_once_with("octocat", None, None)

    def test_fetch_gists_trims_response(self):
        with self._mock_urlopen(self.SAMPLE):
            gists = app.fetch_gists("octocat")
        self.assertEqual(gists, [{
            "id": "abc123",
            "description": "hello world",
            "url": "https://gist.github.com/octocat/abc123",
            "files": ["hello.py"],
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2020-01-02T00:00:00Z",
        }])

    def test_pagination_is_passed_through(self):
        with mock.patch("app.fetch_gists", return_value=[]) as fetch:
            status, _ = get(self.base, "/octocat?page=2&per_page=5")
        self.assertEqual(status, 200)
        fetch.assert_called_once_with("octocat", "2", "5")

    def test_unknown_user_returns_404(self):
        with mock.patch("app.fetch_gists",
                        side_effect=app.UpstreamError(404, "user 'x' not found")):
            status, body = get(self.base, "/x")
        self.assertEqual(status, 404)
        self.assertIn("not found", body["error"])

    def test_invalid_username_returns_400(self):
        status, _ = get(self.base, "/not_a-valid--name")
        self.assertEqual(status, 400)

    def test_invalid_page_returns_400(self):
        status, _ = get(self.base, "/octocat?page=abc")
        self.assertEqual(status, 400)


@unittest.skipIf(os.environ.get("SKIP_LIVE") == "1", "live GitHub test disabled")
class TestLiveGitHub(ServerTestCase):
    """Integration test against the real GitHub API using octocat."""

    def test_octocat_has_public_gists(self):
        status, body = get(self.base, "/octocat")
        self.assertEqual(status, 200)
        self.assertGreater(body["count"], 0)
        for gist in body["gists"]:
            self.assertIn("id", gist)
            self.assertTrue(gist["url"].startswith("https://gist.github.com/"))


if __name__ == "__main__":
    unittest.main()
