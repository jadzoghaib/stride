"""Reading a proof page, so a human does not have to.

Admission holds a genuine athlete below the listing line until somebody opens a
URL and confirms their name is on it. The financial model puts that queue at
250 reviews per 1,000 applicants; the cost is not the labour — it peaks around
0.6 of one reviewer — it is the *latency*. An athlete sitting in the queue is
not listed, not matchable and not earning. This closes that gap for the cases
that are unambiguous, and only those.

Three rules, in descending order of how much trouble ignoring them causes.

**1. The URL is hostile input.** It is a string an applicant typed, fetched by
our server from inside our network. That is textbook SSRF: `http://localhost`,
the cloud metadata endpoint at 169.254.169.254, anything on a private range.
Every hostname is resolved and every resolved address checked before a socket is
opened, and again on each redirect hop — a domain that resolves publicly can
redirect to `127.0.0.1`, and checking only the first URL catches nothing.

**2. Silence is not consent.** A fetch that times out, 404s, returns something
that is not text, or returns a page the name is not plainly on, leaves the
application exactly where it was: in the human queue. Nothing here can admit
anybody on its own; it can only agree with a claim, and only when the agreement
is unambiguous.

**3. No JavaScript, ever.** A roster rendered client-side is not readable here
and is not meant to be — running fetched script server-side would hand an
applicant code execution. Those stay for the human queue, which is the honest
answer rather than a headless browser nobody is auditing.
"""

from __future__ import annotations

import ipaddress
import re
import socket
import unicodedata
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

TIMEOUT_SECONDS = 6.0
MAX_BYTES = 512_000
MAX_REDIRECTS = 3
USER_AGENT = "StrideProofCheck/1.0 (+https://stride.example/proof-check)"

_TAG = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.I | re.S)
_ANY_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


@dataclass
class ProofResult:
    """What a fetch concluded, and why. `verified` is the only status that
    changes anything; every other outcome leaves the application in the queue."""
    status: str            # verified | unverified
    reason: str            # machine-readable, recorded on the event
    detail: str = ""       # short human sentence for the ops queue
    matched: str = ""      # the form of the name that was found

    @property
    def conclusive(self) -> bool:
        return self.status == "verified"


def normalise(text: str) -> str:
    """Casefold, strip accents, collapse whitespace.

    Accents are stripped so that a roster spelling `Vallès` matches a profile
    typed `Valles`, which is the single most common false negative in a Spanish
    market and not worth sending a human.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACE.sub(" ", stripped.casefold()).strip()


def page_text(html: str) -> str:
    body = _TAG.sub(" ", html)
    return normalise(_ANY_TAG.sub(" ", body))


def name_on_page(name: str, text: str) -> str | None:
    """The name as it was found, or None.

    Deliberately strict. `"John Smith"` matches "john smith" and "smith, john"
    and nothing else — not "john" alone, and not "smith" alone, because a
    surname on a club page is not evidence about a person. A false positive here
    admits someone on a check that did not happen, which is worse than any
    number of false negatives: those cost a reviewer four minutes.
    """
    tokens = [t for t in normalise(name).split(" ") if len(t) > 1]
    if len(tokens) < 2:
        return None                       # a single token is not identifying
    forms = [" ".join(tokens), ", ".join([tokens[-1], " ".join(tokens[:-1])])]
    for form in forms:
        if re.search(rf"(?<![a-z0-9]){re.escape(form)}(?![a-z0-9])", text):
            return form
    return None


def looks_openable(url: str) -> bool:
    """Is there a page here at all?

    Structural only — scheme and host — with no DNS lookup, because this also
    guards the *human* path where a reviewer has already opened the link and a
    resolution failure on our side is not evidence about theirs. `"http://"` is
    the case that matters: it passes a naive scheme test, passes a non-empty
    test, and there is nothing behind it to look at.
    """
    parsed = urlparse((url or "").strip())
    return parsed.scheme in ("http", "https") and bool(parsed.hostname)


def _address_is_public(host: str) -> bool:
    """Resolve and reject anything that is not a public unicast address.

    Checked per hop rather than once: a public domain can redirect to loopback,
    and validating only the URL an applicant typed would miss exactly the
    request an attacker wants us to make.
    """
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            return False
    return True


def safe_url(url: str) -> tuple[bool, str]:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in ("http", "https"):
        return False, "scheme_not_http"
    if not parsed.hostname:
        return False, "no_host"
    if not _address_is_public(parsed.hostname):
        return False, "host_not_public"
    return True, ""


def fetch(url: str) -> tuple[str | None, str]:
    """Return (text, reason). `text` is None when nothing readable came back.

    Redirects are followed by hand so each hop can be re-checked, and the body
    is read in chunks so a hostile server cannot stream us out of memory by
    lying about Content-Length.
    """
    for _ in range(MAX_REDIRECTS + 1):
        ok, why = safe_url(url)
        if not ok:
            return None, why
        try:
            with httpx.Client(follow_redirects=False, timeout=TIMEOUT_SECONDS) as client:
                with client.stream("GET", url, headers={"User-Agent": USER_AGENT}) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            return None, "redirect_without_location"
                        url = str(response.next_request.url) if response.next_request else location
                        continue
                    if response.status_code != 200:
                        return None, f"http_{response.status_code}"
                    kind = response.headers.get("content-type", "")
                    if "html" not in kind and "text/plain" not in kind:
                        return None, "not_text"
                    chunks, size = [], 0
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            return None, "too_large"
                        chunks.append(chunk)
                    body = b"".join(chunks).decode(response.encoding or "utf-8", "replace")
                    return body, "ok"
        except httpx.TimeoutException:
            return None, "timeout"
        except httpx.HTTPError as exc:
            return None, f"fetch_error:{type(exc).__name__}"
    return None, "too_many_redirects"


def check(url: str, name: str, fetcher=fetch) -> ProofResult:
    """The whole decision. `fetcher` is injectable so tests never touch a socket."""
    if not (url or "").strip():
        return ProofResult("unverified", "no_url", "No link supplied — nothing to open.")
    body, reason = fetcher(url)
    if body is None:
        return ProofResult("unverified", reason,
                           f"Could not read the page ({reason}) — left for a human.")
    found = name_on_page(name, page_text(body))
    if not found:
        return ProofResult("unverified", "name_not_found",
                           "Page loaded, but the applicant's name is not plainly on it.")
    return ProofResult("verified", "name_found",
                       f"Found “{found}” on the page.", matched=found)
