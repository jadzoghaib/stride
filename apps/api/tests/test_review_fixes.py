"""Three defaults that were wrong in a way only production would reveal.

Each of these passed every existing test because the tests run against the
socket, in `dev`, with a calendar year of birth that happened to be safe.
"""

from __future__ import annotations


import pytest
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from stride_api.admission import MIN_AGE, admission_decision, age_from, athlete_credibility
from stride_api.config import Settings
from stride_api.main import app

BAD = {"email": "nobody@nowhere.test", "password": "wrong-pass"}


def _hammer(c: TestClient, ip: str, n: int = 30) -> list[int]:
    return [c.post("/api/auth/login", json=BAD, headers={"X-Forwarded-For": ip}).status_code
            for _ in range(n)]


# ── rate limiting behind a proxy ────────────────────────────────────────────

def test_forwarded_for_is_ignored_when_no_proxy_is_trusted(client):
    """The default. A client cannot escape the limiter by inventing a header:
    both "addresses" share the socket peer's bucket, so the second is limited
    by the first's attempts."""
    assert _hammer(client, "10.0.0.1")[-1] == 429
    assert client.post("/api/auth/login", json=BAD,
                       headers={"X-Forwarded-For": "10.0.0.2"}).status_code == 429


def test_behind_a_trusted_proxy_each_client_has_its_own_bucket():
    """The deployment. Behind the ingress every request arrives from one
    address; without honouring the forwarded header, twenty bad logins from
    anyone locked the login endpoint for everyone. With the proxy trusted, the
    limiter keys on the real client and a second person is unaffected."""
    with TestClient(ProxyHeadersMiddleware(app, trusted_hosts="*")) as c:
        assert _hammer(c, "10.0.0.1")[-1] == 429
        # a different person, same ingress: not locked out
        assert c.post("/api/auth/login", json=BAD,
                      headers={"X-Forwarded-For": "10.0.0.2"}).status_code == 401


def test_trusted_proxies_come_from_the_environment(monkeypatch):
    monkeypatch.delenv("STRIDE_FORWARDED_ALLOW_IPS", raising=False)
    assert Settings().forwarded_allow_ips == []
    monkeypatch.setenv("STRIDE_FORWARDED_ALLOW_IPS", "*")
    assert Settings().forwarded_allow_ips == ["*"]
    monkeypatch.setenv("STRIDE_FORWARDED_ALLOW_IPS", "10.0.0.5, 10.0.0.6 ,")
    assert Settings().forwarded_allow_ips == ["10.0.0.5", "10.0.0.6"]


# ── chaos is opt-in outside dev ─────────────────────────────────────────────

@pytest.mark.parametrize("env,expected", [("dev", True), ("test", True),
                                          ("production", False), ("staging", False)])
def test_chaos_injection_defaults_off_outside_dev(monkeypatch, env, expected):
    """The old default was "on everywhere, remember to turn it off". A
    deployment that forgot the flag would have served 503s on purpose."""
    monkeypatch.delenv("STRIDE_CHAOS", raising=False)
    monkeypatch.setenv("STRIDE_ENV", env)
    if env not in ("dev", "test"):
        monkeypatch.setenv("STRIDE_SECRET", "x" * 64)  # prod refuses the dev secret
    assert Settings().chaos_enabled is expected


def test_chaos_can_still_be_forced_on_explicitly(monkeypatch):
    monkeypatch.setenv("STRIDE_ENV", "staging")
    monkeypatch.setenv("STRIDE_SECRET", "x" * 64)
    monkeypatch.setenv("STRIDE_CHAOS", "1")
    assert Settings().chaos_enabled is True


# ── a year of birth is a bound, not an age ──────────────────────────────────

def test_a_year_of_birth_yields_the_lowest_possible_age():
    """Born some day in 2010, today some day in 2026: fifteen or sixteen. The
    gate must assume fifteen. The previous arithmetic said sixteen for the
    whole calendar year, admitting people who would not turn sixteen until
    December."""
    assert age_from(2010, today_year=2026) == 15
    assert age_from(2009, today_year=2026) == 16
    assert age_from(None, today_year=2026) is None


def test_the_boundary_year_is_refused_as_under_age():
    """The consequence in the decision: the year that used to scrape through
    is now refused, and refused for age rather than parked as incomplete."""
    def verdict(birth_year: int) -> dict:
        application = {"sport": "football", "competition_level": "national",
                       "years_competing": 3, "birth_year": birth_year,
                       "proof_kind": "roster", "proof_status": "verified",
                       "proof_url": "https://club.example/roster"}
        scored = athlete_credibility(application, today_year=2026)
        return admission_decision(scored["credibility"], proof_status="verified",
                                  age=age_from(birth_year, 2026),
                                  scoreable=scored["scoreable"])

    on_the_line = verdict(2026 - MIN_AGE)          # 15 or 16 -> treated as 15
    assert on_the_line["decision"] == "rejected"
    assert on_the_line["rule"] == "under_minimum_age"
    assert verdict(2026 - MIN_AGE - 1)["rule"] != "under_minimum_age"


def test_a_birth_year_in_the_future_is_refused_at_the_edge(athlete):
    """`le=2030` let a typo through as a negative age. The ceiling is now this
    year, so the form says so instead of the gate having to reason about it."""
    r = athlete.post("/api/athlete/application", json={
        "competition_level": "national", "years_competing": 1,
        "birth_year": 2099, "proof_kind": "none", "proof_url": ""})
    assert r.status_code == 422
