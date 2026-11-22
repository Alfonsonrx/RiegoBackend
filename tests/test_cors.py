"""CORS for the web UI (frontend served on another origin). Not tied to a spec bullet yet: see specs/backlog.md."""
from app.config import Settings

UI = "http://localhost:8080"


def preflight(client, origin, method="POST", headers="authorization,content-type", path="/schedules"):
    return client.options(path, headers={"Origin": origin, "Access-Control-Request-Method": method,
                                         "Access-Control-Request-Headers": headers})


def test_cors_preflight_allows_the_ui_methods_and_headers(client):
    for origin in (UI, "http://127.0.0.1:8080"):
        for method in ("GET", "POST", "PATCH"):
            r = preflight(client, origin, method)
            assert r.status_code == 200, (origin, method)
            assert r.headers["access-control-allow-origin"] == origin
            assert method in r.headers["access-control-allow-methods"]
            assert {"authorization", "content-type"} <= {h.strip().lower() for h in
                                                         r.headers["access-control-allow-headers"].split(",")}
            assert "access-control-allow-credentials" not in r.headers  # bearer tokens, no cookies


def test_cors_answers_carry_the_origin_even_when_refused(client):
    r = client.get("/sensors", headers={"Origin": UI})
    assert r.status_code == 401  # no token: refused, but the browser can still read why
    assert r.headers["access-control-allow-origin"] == UI


def test_cors_other_origins_and_methods_not_allowed(client):
    assert preflight(client, "http://evil.example").status_code == 400
    assert "access-control-allow-origin" not in client.get("/sensors", headers={"Origin": "http://evil.example"}).headers
    assert preflight(client, UI, "DELETE").status_code == 400


def test_cors_origins_come_from_settings(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://riego.example"]')
    assert Settings(_env_file=None).CORS_ORIGINS == ["https://riego.example"]
    monkeypatch.delenv("CORS_ORIGINS")
    assert Settings(_env_file=None).CORS_ORIGINS == [UI, "http://127.0.0.1:8080"]
