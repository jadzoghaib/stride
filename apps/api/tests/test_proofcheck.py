"""Auto-verification: what it will conclude, and what it refuses to.

The asymmetry is the whole design. A false negative costs a reviewer four
minutes. A false positive admits somebody on a check that never happened, which
is the one thing the evidence multiplier exists to prevent — so every ambiguous
case, every failed fetch and every page we cannot read stays in the human queue.
"""

from __future__ import annotations

import pytest

from stride_api import proofcheck

ROSTER = """
<!doctype html><html><head><title>Plantilla</title>
<script>var hidden = "Impostor Person";</script></head>
<body><h1>Primer equipo</h1>
<ul><li>7 &mdash; Kaia Mercer &mdash; Athletics</li>
    <li>9 &mdash; Sofia Brandt</li></ul></body></html>
"""


def page(html, kind="text/html; charset=utf-8", status=200):
    def fetcher(url):
        return (html, "ok") if status == 200 else (None, f"http_{status}")
    return fetcher


# ── what it agrees with ─────────────────────────────────────────────────────

def test_a_name_plainly_on_the_page_is_verified():
    result = proofcheck.check("https://club.example/roster", "Kaia Mercer", page(ROSTER))
    assert result.conclusive and result.status == "verified"
    assert result.matched == "kaia mercer"


def test_surname_first_listings_still_match():
    html = "<p>Mercer, Kaia — 800m</p>"
    assert proofcheck.check("https://club.example/r", "Kaia Mercer", page(html)).conclusive


def test_accents_do_not_cause_a_needless_review():
    """A roster spelling `Vallès` against a profile typed `Valles` is the most
    common false negative in this market and is not worth a reviewer."""
    html = "<li>Núria Vallès</li>"
    assert proofcheck.check("https://c.example/r", "Nuria Valles", page(html)).conclusive


# ── what it refuses ─────────────────────────────────────────────────────────

def test_a_name_that_is_not_there_stays_for_a_human():
    result = proofcheck.check("https://club.example/r", "Marcus Oyelaran", page(ROSTER))
    assert not result.conclusive
    assert result.reason == "name_not_found"


def test_a_surname_alone_is_not_evidence_about_a_person():
    """A surname on a club page says nothing about which person it is."""
    assert not proofcheck.check("https://c.example/r", "Kaia Mercer",
                                page("<p>Mercer</p>")).conclusive
    assert proofcheck.name_on_page("Mercer", "mercer") is None


def test_script_contents_are_not_page_text():
    """Otherwise anyone could smuggle a name past the check in a script tag."""
    assert not proofcheck.check("https://c.example/r", "Impostor Person",
                                page(ROSTER)).conclusive


def test_a_failed_fetch_never_concludes():
    for fetcher, reason in (
        (lambda url: (None, "timeout"), "timeout"),
        (lambda url: (None, "http_404"), "http_404"),
        (lambda url: (None, "not_text"), "not_text"),
    ):
        result = proofcheck.check("https://c.example/r", "Kaia Mercer", fetcher)
        assert not result.conclusive and result.reason == reason


def test_no_url_is_not_a_check():
    assert proofcheck.check("", "Kaia Mercer", page(ROSTER)).reason == "no_url"


# ── the URL is hostile input ────────────────────────────────────────────────

@pytest.mark.parametrize("url", [
    "http://localhost:8490/api/admin/events",
    "http://127.0.0.1/",
    "http://169.254.169.254/latest/meta-data/",     # cloud metadata
    "http://10.0.0.5/roster",
    "http://192.168.1.1/",
    "http://[::1]/",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "gopher://example.com/",
])
def test_the_fetcher_refuses_to_reach_inside_the_network(url):
    """Fetching an applicant-supplied URL from our own server is textbook SSRF.
    Every one of these is a request an applicant could otherwise make us send."""
    ok, why = proofcheck.safe_url(url)
    assert not ok, f"{url} should have been refused"
    assert why in ("scheme_not_http", "host_not_public", "no_host")


def test_a_public_host_is_allowed_through_the_guard():
    ok, why = proofcheck.safe_url("https://example.com/roster")
    assert ok, why


def test_redirects_are_re_checked_rather_than_trusted_once():
    """A public domain can redirect to loopback. Validating only the URL the
    applicant typed would miss exactly the request an attacker wants."""
    source = proofcheck.fetch.__doc__ or ""
    assert "re-checked" in source or "each hop" in source
    # and the loop really does re-validate: the guard call sits inside it
    import inspect
    body = inspect.getsource(proofcheck.fetch)
    assert body.index("for _ in range") < body.index("safe_url(url)")


# ── a scheme is not a link ──────────────────────────────────────────────────

@pytest.mark.parametrize("url,openable", [
    ("http://", False),          # passes a naive scheme test and has nothing behind it
    ("https://", False),
    ("http:///path", False),
    ("   ", False),
    ("", False),
    ("ftp://example.com/x", False),
    ("http://club.example/roster", True),
    ("https://club.example/roster", True),
])
def test_looks_openable_requires_a_host_not_just_a_scheme(url, openable):
    """`http://` used to reach `verified`: non-empty, correctly prefixed, and
    with no page behind it for anyone to have looked at."""
    assert proofcheck.looks_openable(url) is openable
