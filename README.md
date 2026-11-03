# Gists API

A small HTTP API that returns a GitHub user's public gists.

`GET /<user>` returns the user's gists from the [GitHub Gists API](https://docs.github.com/en/rest/gists/gists?apiVersion=2022-11-28#list-gists-for-a-user).

Written in Python using only the standard library, so there's nothing to install apart from Python (or Docker).

## Run with Docker

```sh
docker build -t task-eli .
docker run --rm -p 8080:8080 --name task-eli task-eli
```

The unit tests run as part of the image build, so the build fails if they fail.

Then:

```sh
curl http://localhost:8080/octocat
```

## Run locally (Python 3.9+)

```sh
python app.py
```

## Tests

```sh
python -m unittest -v test_app
```

- `TestGistsApi` - unit tests, GitHub is mocked so they run offline.
- `TestLiveGitHub` - calls the real GitHub API for `octocat`. Skip it with `SKIP_LIVE=1`.

## API

| Request | Response |
|---|---|
| `GET /octocat` | `200` with `{"user", "count", "gists": [...]}` |
| `GET /octocat?page=2&per_page=10` | Pagination, passed straight through to GitHub |
| `GET /<unknown-user>` | `404` |
| `GET /bad_name!` | `400` invalid username |
| GitHub rate limit hit | `429` |
| GitHub unreachable / error | `502` |

Example response:

```json
{
  "user": "octocat",
  "count": 1,
  "gists": [
    {
      "id": "6cad326836d38bd3a7ae",
      "description": "Hello world!",
      "url": "https://gist.github.com/octocat/6cad326836d38bd3a7ae",
      "files": ["hello_world.rb"],
      "created_at": "2014-10-01T16:19:34Z",
      "updated_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

Each gist is trimmed down to the useful fields rather than returning GitHub's full payload.

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `PORT` | `8080` | |
| `GITHUB_TOKEN` | unset | Optional. Unauthenticated requests are limited to 60/hour. |

```sh
docker run --rm -p 8080:8080 -e GITHUB_TOKEN=... task-eli
```

## Notes / things I'd add with more time

- Caching responses (with ETags) to save on rate limit.
- Following GitHub's `Link` header to return all pages instead of passing pagination through.
- A health endpoint and structured logging.
