"""Admission: athlete applications, club verification, and club nominations.

One router rather than three, because this is a single policy with three doors
into it. Scoring lives in `..admission`; everything here is persistence, the
decision's effect on what the world can see, and the audit trail.

Two behaviours are worth reading before the code:

**Admission gates listing, it does not replace it.** An admitted athlete becomes
`listed` only if there is something to show — otherwise `draft`, until they
connect a platform. Credibility decides whether you are *allowed* in; measured
analytics decide whether you are *worth showing*. Profiles with no application
are left alone, so the seeded directory predates the gate rather than being
retroactively delisted by it.

**A nomination is a floor, not a bypass.** A verified club vouching for an
athlete raises that athlete's credibility, but cannot supply their date of birth
or their competition level — so a nominated athlete who has submitted nothing
still lands in review, and the 16+ age gate still cannot be cleared by a third
party's assertion. Minting a thousand athletes therefore costs a thousand
completed forms, not one API call. The nomination is also bounded by the roster
size the club itself declared, which makes inflating that number a checkable
claim rather than free headroom.
"""

from __future__ import annotations

import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from statistics import median

from creatorlens.analytics.scoring import latest_score
from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator

from ..admission import (age_of, ADMIT_AT, COMPETITION_LEVELS, DISQUALIFYING_RULES,
                         PROOF_KINDS, PROOF_STATUSES,
                         POLICY_VERSION, admission_decision, age_from,
                         athlete_credibility, club_legitimacy)
from ..auth import get_db, require_role
from .. import proofcheck
from ..db import lock_for_update, now_iso, row, rows
from .messaging import notify

# A year of birth in the future is a typo, not a minor; refuse it at the edge.
_THIS_YEAR = datetime.now(timezone.utc).year

router = APIRouter(prefix="/api", tags=["admission"])

SCORE_KEYS = ("audience_scale", "engagement_quality", "audience_fit", "growth", "consistency")


def _social_score(conn, creator_id: int | None) -> float | None:
    """One number from the analytics, for the fraud signal only.

    The mean over the dimensions CreatorLens actually measured — and here
    renormalising over what is present is right, precisely because these are
    platform measurements rather than applicant claims. An athlete does not
    choose whether Instagram returned data; they do choose what to type on a
    form. That asymmetry is why this module treats the two kinds of gap in
    opposite ways.
    """
    if not creator_id:
        return None
    snap = latest_score(conn, creator_id)
    if snap is None:
        return None
    measured = [snap[k] for k in SCORE_KEYS if snap[k] is not None]
    return sum(measured) / len(measured) if measured else None


def _own_athlete(conn, user) -> dict:
    profile = row(conn, "SELECT * FROM athlete_profiles WHERE user_id = ?", (user["id"],))
    if profile is None:
        raise HTTPException(404, "no_athlete_profile")
    return profile


def _own_club(conn, user) -> dict:
    club = row(conn, "SELECT * FROM clubs WHERE user_id = ?", (user["id"],))
    if club is None:
        raise HTTPException(404, "no_club")
    return club


def _club_floor(conn, club_id: int | None) -> float:
    """What a nominating club is currently worth. Recomputed on every decision,
    so losing verification withdraws the floor without a migration."""
    if not club_id:
        return 0.0
    app = row(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club_id,))
    if app is None or app["decision"] != "verified":
        return 0.0
    return club_legitimacy(app)["nomination_floor"]


def _admitted_via(via: str, granted: bool, listing: str, application: dict) -> str:
    """How this profile got into the directory, or "" if it is not in it.

    The middle case is the one worth naming: a verdict that would have delisted
    somebody but was held back by `may_delist=False` — a nomination arriving for
    an athlete the gate had already admitted. Clearing the marker there left a
    listing the gate granted looking like one that predates it, which made it
    grandfathered, which meant no later reviewer could take it away.
    """
    if granted:
        return via
    return "" if listing == "draft" else application["admitted_via"]


def _evaluate(conn, application: dict, profile: dict, *, via: str,
              may_delist: bool = True) -> dict:
    """Score, decide, persist, and align what the directory shows. Idempotent.

    `may_delist=False` for anything a third party triggers. A club nominating an
    athlete who has never filled in a form produces a `review` decision, and
    without this that verdict would knock a perfectly healthy listed profile
    down to draft — someone else's action costing that athlete their standing.
    A nomination is a ratchet: it can raise a listing, never lower one.

    A second, quieter ratchet is applied here rather than by the caller. A
    profile listed before the gate existed keeps that listing through any
    *inconclusive* verdict, however it was triggered: the seeded directory is
    grandfathered on purpose, and an application is a request to be admitted,
    not a re-audit of standing granted beforehand. Computing this at the call
    site is what went wrong the first time — the self-submit path had it and the
    two reviewer paths did not, so the protection held when the athlete touched
    their own form and vanished when an admin touched it.

    Two things end it, both adverse findings rather than absences:

      * `admitted_via` set — the gate granted this listing, so the gate may take
        it back when the claim behind it is weakened;
      * a disqualifying *rule* — see `DISQUALIFYING_RULES`. Keying this to the
        proof status alone let a declared age below the minimum keep a
        grandfathered listing, and the age gate is the one rule here that
        nothing may buy its way past. Keying it to any `rejected` decision went
        too far the other way: a claim scoring below the review band is a weak
        application, not a finding, and a listing that predates the gate should
        survive an athlete filling the form in badly.
    """
    scored = athlete_credibility({**application, "sport": profile["sport"]})
    social = _social_score(conn, profile["creatorlens_creator_id"])
    decision = admission_decision(
        scored["credibility"],
        proof_status=application["proof_status"],
        social_score=social,
        age=age_of(application),
        club_floor=_club_floor(conn, application["nominated_by_club"]),
        scoreable=scored["scoreable"],
    )
    admitted = decision["decision"] == "admitted"

    # Computed here rather than at the top, because it depends on the verdict:
    # a rejection ends grandfathering, and only the decision knows about the age
    # gate. `may_delist=False` from a caller still wins — a nomination may never
    # lower a listing whatever it concludes.
    if may_delist:
        pre_gate = (profile["status"] == "listed"
                    and not application["admitted_via"]
                    and decision["rule"] not in DISQUALIFYING_RULES)
        may_delist = not pre_gate

    # Gate on legitimacy, tier on value: admitted with no analytics is still a
    # draft profile, because there is nothing for a sponsor to look at yet.
    #
    # The test is a *score*, not a creator id. It used to be the id, which was a
    # fair proxy while creator records were made on first platform connect — but
    # registration creates one immediately, so the condition became "is an
    # athlete" and was true for everybody. A newly admitted account with nothing
    # connected went straight into the directory and into sponsor matching with
    # no data behind it, which is the exact outcome this line exists to prevent.
    has_analytics = (bool(profile["creatorlens_creator_id"])
                     and latest_score(conn, profile["creatorlens_creator_id"]) is not None)
    granted = admitted and has_analytics
    listing = "listed" if granted else "draft"
    if listing == "draft" and not may_delist:
        listing = profile["status"]
    # A freeze outranks everything above it. The club that vouched for this
    # athlete withdrew it, and re-running the scorer must not quietly put them
    # back -- the way out is a new link or a reviewer, both of which clear the
    # flag before this line is reached again.
    if profile["frozen_at"]:
        listing = "draft"

    # `admitted_via` records how the gate put someone in the directory, and is
    # what later tells us their listing was earned here rather than inherited.
    # Writing it on an admission that produced no listing — admitted, but no
    # analytics to show — ended a grandfathered athlete's protection by
    # succeeding: the next inconclusive review then delisted them on the
    # strength of a listing the gate had never actually granted.
    conn.execute(
        "UPDATE athlete_applications SET credibility = ?, decision = ?, decision_rule = ?,"
        " admitted_via = ?, policy_version = ?, decided_at = ? WHERE id = ?",
        (scored["credibility"], decision["decision"], decision["rule"],
         _admitted_via(via, granted, listing, application), POLICY_VERSION,
         now_iso(), application["id"]))
    conn.execute("UPDATE athlete_profiles SET status = ? WHERE id = ?",
                 (listing, profile["id"]))

    log_event(conn, "system", "admission.decided", "athlete", profile["id"],
              {"application_id": application["id"], "decision": decision["decision"],
               "rule": decision["rule"], "credibility": scored["credibility"],
               "effective_credibility": decision["effective_credibility"],
               "components": scored["components"], "missing": scored["missing"],
               "evidence_multiplier": scored["evidence_multiplier"],
               "social_score": round(social, 1) if social is not None else None,
               "nominated_by_club": application["nominated_by_club"],
               "listing": listing, "policy_version": POLICY_VERSION})
    conn.commit()
    return {**scored, **decision, "listing": listing,
            "social_score": round(social, 1) if social is not None else None}


# ── athlete ─────────────────────────────────────────────────────────────────
class ApplicationIn(BaseModel):
    competition_level: str = Field(default="", max_length=20)
    discipline: str = Field(default="", max_length=80)
    club_name: str = Field(default="", max_length=120)
    league_name: str = Field(default="", max_length=120)
    years_competing: int | None = Field(default=None, ge=0, le=60)
    birth_year: int | None = Field(default=None, ge=1930, le=_THIS_YEAR)
    # The form sends this now; the year is derived from it so every reader of
    # birth_year keeps working. A year on its own is still accepted, because
    # older clients and clubs (who cannot know a date) send only that.
    birth_date: str | None = Field(default=None, max_length=10)
    proof_url: str = Field(default="", max_length=500)
    proof_kind: str = Field(default="none", max_length=20)

    @field_validator("birth_date")
    @classmethod
    def _real_past_date(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        try:
            born = date.fromisoformat(v)
        except ValueError as e:
            raise ValueError("birth_date must be an ISO date, YYYY-MM-DD") from e
        if born.year < 1930 or born > datetime.now(timezone.utc).date():
            raise ValueError("birth_date must be a real date in the past")
        return born.isoformat()

    @model_validator(mode="after")
    def _year_follows_date(self):
        if self.birth_date:
            self.birth_year = int(self.birth_date[:4])
        return self


@router.post("/athlete/application", status_code=201)
def submit_application(body: ApplicationIn,
                       user: dict = Depends(require_role("athlete")),
                       conn: sqlite3.Connection = Depends(get_db)):
    """Submit or replace an application. Re-submitting resets proof to unverified:
    changing the claim invalidates whatever was checked against the old one."""
    if body.competition_level and body.competition_level not in COMPETITION_LEVELS:
        raise HTTPException(422, "unknown_competition_level")
    if body.proof_kind not in PROOF_KINDS:
        raise HTTPException(422, "unknown_proof_kind")
    profile = _own_athlete(conn, user)
    existing = row(conn, "SELECT * FROM athlete_applications WHERE athlete_id = ?",
                   (profile["id"],))
    # A supplied link starts life queued for checking, not trusted.
    proof_status = "pending" if body.proof_kind != "none" and body.proof_url else "unverified"
    # ...unless a check has already failed. A rejected verification is a finding
    # about the applicant, not about the URL, so only a reviewer can clear it —
    # otherwise re-submitting launders a caught forgery back to a clean slate.
    if existing and existing["proof_status"] == "rejected":
        proof_status = "rejected"
    fields = (body.discipline, body.club_name, body.league_name, body.competition_level,
              body.years_competing, body.birth_year, body.birth_date, body.proof_url,
              body.proof_kind, proof_status)
    if existing:
        conn.execute(
            "UPDATE athlete_applications SET discipline = ?, club_name = ?, league_name = ?,"
            " competition_level = ?, years_competing = ?, birth_year = ?, birth_date = ?,"
            " proof_url = ?, proof_kind = ?, proof_status = ? WHERE id = ?", (*fields, existing["id"]))
        application_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO athlete_applications (athlete_id, discipline, club_name, league_name,"
            " competition_level, years_competing, birth_year, birth_date, proof_url, proof_kind,"
            " proof_status, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (profile["id"], *fields, now_iso()))
        application_id = cur.lastrowid
    application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?", (application_id,))

    # Applying must not cost an athlete the listing they already had — see
    # `_evaluate`, which owns that rule so every path through the gate gets it.
    return _evaluate(conn, application, profile, via="self")


@router.get("/athlete/application")
def my_application(user: dict = Depends(require_role("athlete")),
                   conn: sqlite3.Connection = Depends(get_db)):
    """The applicant's own decision, decomposed. A gate whose result cannot be
    explained to the person it excluded is a gate they cannot appeal."""
    profile = _own_athlete(conn, user)
    application = row(conn, "SELECT * FROM athlete_applications WHERE athlete_id = ?",
                      (profile["id"],))
    if application is None:
        return {"application": None, "thresholds": {"admit": ADMIT_AT}}
    scored = athlete_credibility({**application, "sport": profile["sport"]})
    # `thresholds` on both branches. It was sent only when there was no
    # application, so every applicant who actually had one — i.e. everyone this
    # page is for — fell through to the client's hard-coded `?? 55`. Move
    # ADMIT_AT and the applicant would be shown one bar while being judged
    # against another, which is precisely what a page that exists to explain a
    # decision must not do.
    frozen = row(conn, "SELECT p.frozen_at, c.name AS club FROM athlete_profiles p"
                       " LEFT JOIN clubs c ON c.id = p.frozen_by_club WHERE p.id = ?",
                 (profile["id"],))
    return {"application": application, "scored": scored,
            "frozen": {"at": frozen["frozen_at"], "club": frozen["club"]}
                      if frozen and frozen["frozen_at"] else None,
            "thresholds": {"admit": ADMIT_AT},
            "club_floor": _club_floor(conn, application["nominated_by_club"])}


# ── club ────────────────────────────────────────────────────────────────────
class ClubApplicationIn(BaseModel):
    legal_name: str = Field(default="", max_length=160)
    registration_id: str = Field(default="", max_length=60)
    federation_name: str = Field(default="", max_length=160)
    federation_id: str = Field(default="", max_length=60)
    founded_year: int | None = Field(default=None, ge=1800, le=2030)
    competition_level: str = Field(default="", max_length=20)
    teams_count: int | None = Field(default=None, ge=0, le=200)
    registered_athletes: int = Field(default=0, ge=0, le=5000)
    roster_url: str = Field(default="", max_length=500)
    proof_kind: str = Field(default="none", max_length=20)


@router.post("/club/application", status_code=201)
def submit_club_application(body: ClubApplicationIn,
                            user: dict = Depends(require_role("club")),
                            conn: sqlite3.Connection = Depends(get_db)):
    if body.proof_kind not in PROOF_KINDS:
        raise HTTPException(422, "unknown_proof_kind")
    club = _own_club(conn, user)
    proof_status = "pending" if body.proof_kind != "none" and body.roster_url else "unverified"
    payload = body.model_dump() | {"proof_status": proof_status}
    scored = club_legitimacy(payload)
    existing = row(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club["id"],))
    fields = (body.legal_name, body.registration_id, body.federation_name, body.federation_id,
              body.founded_year, body.competition_level, body.teams_count,
              body.registered_athletes, body.roster_url, body.proof_kind, proof_status,
              scored["legitimacy"], scored["decision"], POLICY_VERSION, now_iso())
    if existing:
        conn.execute(
            "UPDATE club_applications SET legal_name = ?, registration_id = ?,"
            " federation_name = ?, federation_id = ?, founded_year = ?, competition_level = ?,"
            " teams_count = ?, registered_athletes = ?, roster_url = ?, proof_kind = ?,"
            " proof_status = ?, legitimacy = ?, decision = ?, policy_version = ?,"
            " decided_at = ? WHERE id = ?", (*fields, existing["id"]))
    else:
        conn.execute(
            "INSERT INTO club_applications (club_id, legal_name, registration_id,"
            " federation_name, federation_id, founded_year, competition_level, teams_count,"
            " registered_athletes, roster_url, proof_kind, proof_status, legitimacy, decision,"
            " policy_version, decided_at, submitted_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (club["id"], *fields, now_iso()))
    log_event(conn, "system", "club.eligibility_decided", "club", club["id"],
              {"legitimacy": scored["legitimacy"], "decision": scored["decision"],
               "components": scored["components"], "missing": scored["missing"],
               "evidence_multiplier": scored["evidence_multiplier"],
               "policy_version": POLICY_VERSION})
    conn.commit()
    return scored


@router.get("/club/application")
def my_club_application(user: dict = Depends(require_role("club")),
                        conn: sqlite3.Connection = Depends(get_db)):
    club = _own_club(conn, user)
    application = row(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club["id"],))
    if application is None:
        return {"application": None}
    used = row(conn, "SELECT COUNT(*) AS n FROM athlete_applications"
               " WHERE nominated_by_club = ?", (club["id"],))["n"]
    return {"application": application, "scored": club_legitimacy(application),
            "nominations": {"used": used, "budget": application["registered_athletes"]}}


class NominationIn(BaseModel):
    athlete_slug: str = Field(min_length=1, max_length=120)


@router.post("/club/nominations", status_code=201)
def nominate(body: NominationIn, user: dict = Depends(require_role("club")),
             conn: sqlite3.Connection = Depends(get_db)):
    """Vouch for an athlete. Raises their credibility floor; never admits them
    outright — see this module's docstring for why that distinction is the whole
    security model of club onboarding."""
    club = _own_club(conn, user)

    # Counting and then inserting is only a budget if nothing slips between the
    # two. Two nominations posted together both read the old total, both find
    # room, and both write — so a club could mint more floors than the roster it
    # declared, which is the one number making that declaration checkable.
    #
    # The lock is taken *before* the read, not after it. Locking and then
    # trusting values fetched beforehand protects nothing: `decision` and
    # `registered_athletes` may both have moved, so a club revoked mid-request
    # would still nominate, against the roster size it used to claim.
    lock_for_update(conn, "club_applications", "club_id", club["id"])
    club_app = row(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club["id"],))
    if club_app is None or club_app["decision"] != "verified":
        raise HTTPException(403, "club_not_verified")

    used = row(conn, "SELECT COUNT(*) AS n FROM athlete_applications"
               " WHERE nominated_by_club = ?", (club["id"],))["n"]
    if used >= club_app["registered_athletes"]:
        raise HTTPException(409, "nomination_budget_exhausted")

    profile = row(conn, "SELECT * FROM athlete_profiles WHERE slug = ?", (body.athlete_slug,))
    if profile is None:
        raise HTTPException(404, "unknown_athlete")

    application = row(conn, "SELECT * FROM athlete_applications WHERE athlete_id = ?",
                      (profile["id"],))
    if application is None:
        # The cold-start path: the club knows things the athlete has not typed
        # yet. Their own fields stay blank, which is exactly why this lands in
        # review rather than admitted.
        cur = conn.execute(
            "INSERT INTO athlete_applications (athlete_id, club_name, competition_level,"
            " nominated_by_club, submitted_at) VALUES (?, ?, ?, ?, ?)",
            (profile["id"], club["name"], "", club["id"], now_iso()))
        application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?",
                          (cur.lastrowid,))
    elif application["nominated_by_club"] == club["id"]:
        raise HTTPException(409, "already_nominated")
    else:
        conn.execute("UPDATE athlete_applications SET nominated_by_club = ? WHERE id = ?",
                     (club["id"], application["id"]))
        application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?",
                          (application["id"],))

    log_event(conn, "user", "club.nominated_athlete", "athlete", profile["id"],
              {"club_id": club["id"], "budget_used": used + 1,
               "budget": club_app["registered_athletes"]})
    return _evaluate(conn, application, profile, via="club_nomination", may_delist=False)


# ── ops ─────────────────────────────────────────────────────────────────────
def _hours(a: str, b: str) -> float:
    return max(0.0, (datetime.fromisoformat(b.replace("Z", "+00:00"))
                     - datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds() / 3600)


@router.get("/admin/admission-speed")
def admission_speed(user: dict = Depends(require_role("admin")),
                    conn: sqlite3.Connection = Depends(get_db)):
    """How long supply waits, measured the same way sponsor speed is.

    Campaign measurement and time-to-first-offer are instrumented; the wait on
    the other side of the marketplace was not, even though the model says manual
    proof review is what holds a genuine athlete below the listing line.

    Same anti-survivorship rule as `_speed_to_first_offer`: the applications
    still waiting are reported beside the median rather than dropped out of it.
    A median over the ones that got through is a statement about the ones that
    got through, and reads fastest exactly when the queue is worst.
    """
    applications = rows(conn, "SELECT decision, decision_rule, submitted_at, decided_at"
                        " FROM athlete_applications")
    to_decision, to_listed = [], []
    waiting = unchecked = pending = 0
    for a in applications:
        if a["decision"] == "review":
            waiting += 1
            if a["decision_rule"] == "evidence_not_checked":
                unchecked += 1
        elif a["decision"] == "pending":
            pending += 1
        if a["decided_at"] and a["submitted_at"]:
            to_decision.append(_hours(a["submitted_at"], a["decided_at"]))
            if a["decision"] == "admitted":
                to_listed.append(_hours(a["submitted_at"], a["decided_at"]))
    return {
        # None, not 0: nothing has been decided yet is a different statement
        # from everything being decided instantly.
        "median_hours_to_decision": round(median(to_decision), 1) if to_decision else None,
        "median_hours_to_listed": round(median(to_listed), 1) if to_listed else None,
        "decided": len(to_decision),
        "listed": len(to_listed),
        "still_waiting": waiting,
        "waiting_on_an_unopened_link": unchecked,
        "never_submitted": pending,
    }


@router.get("/admin/review-queue")
def review_queue(decision: str = Query("review"), limit: int = Query(100, le=500),
                 user: dict = Depends(require_role("admin")),
                 conn: sqlite3.Connection = Depends(get_db)):
    """What needs human eyes, with the reason it landed there."""
    queued = rows(conn, """
        SELECT ap.*, a.slug, a.display_name, a.sport, a.country
        FROM athlete_applications ap JOIN athlete_profiles a ON a.id = ap.athlete_id
        WHERE ap.decision = ? ORDER BY ap.credibility DESC, ap.id LIMIT ?""",
        (decision, limit))
    for item in queued:
        item["scored"] = athlete_credibility(item)
    return queued


@router.get("/admin/club-queue")
def club_queue(decision: str = Query("review"), limit: int = Query(100, le=500),
               user: dict = Depends(require_role("admin")),
               conn: sqlite3.Connection = Depends(get_db)):
    """Clubs waiting on a look, with the reason each is waiting.

    Building the review interface is what exposed the need for this: an admin
    could already record a check against a club, but had no way to discover
    which clubs were waiting for one. An endpoint nobody can navigate to is a
    workflow that does not exist.
    """
    queued = rows(conn, """
        SELECT ca.*, c.slug, c.name, c.sport, c.country
        FROM club_applications ca JOIN clubs c ON c.id = ca.club_id
        WHERE ca.decision = ? ORDER BY ca.legitimacy DESC, ca.id LIMIT ?""",
        (decision, limit))
    for item in queued:
        item["scored"] = club_legitimacy(item)
    return queued


#: Why a proof was refused. A fixed list because "rejected" on its own tells
#: the applicant nothing and tells the next reviewer less -- and because these
#: are the five things that actually go wrong, so they can be counted.
REJECTION_REASONS = {
    "name_not_on_page": "We could not find your name on the page you linked.",
    "link_did_not_open": "The link did not open for us.",
    "wrong_person": "The page shows a different person with a similar name.",
    "not_competitive": "The page does not show competition at the level claimed.",
    "other": "",
}


#: Why a club's roster page was refused. Separate from the athlete list because
#: they fail differently: an athlete is missing from a page, a club is missing
#: from a register.
CLUB_REJECTION_REASONS = {
    "club_not_on_page": "The page you linked does not appear to be this club's roster.",
    "link_did_not_open": "The link did not open for us.",
    "not_a_registered_club": "We could not match the registration or federation details.",
    "roster_too_small": "The roster does not show the number of athletes declared.",
    "other": "",
}


class ProofIn(BaseModel):
    proof_status: str
    #: required when rejecting, ignored otherwise
    reason: str = Field(default="", max_length=40)
    #: the reviewer's own words, sent to the applicant as written
    note: str = Field(default="", max_length=2000)


@router.post("/admin/applications/{application_id}/proof")
def set_proof(application_id: int, body: ProofIn,
              user: dict = Depends(require_role("admin")),
              conn: sqlite3.Connection = Depends(get_db)):
    """Record the outcome of checking a proof link, then re-decide.

    This is the human half of the evidence multiplier. Everything else about the
    application is unchanged — only what we now know about it has moved.
    """
    if body.proof_status not in PROOF_STATUSES:
        raise HTTPException(422, "unknown_proof_status")
    application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?", (application_id,))
    if application is None:
        raise HTTPException(404, "unknown_application")
    # `verified` means somebody opened a link and saw the applicant's name on it.
    # With no link there is nothing to open, so the status cannot be reached —
    # otherwise a high-scoring claim is admitted on a check that never happened,
    # which is the exact hole the whole evidence multiplier exists to close.
    # Structural check, not merely non-empty: `"http://"` is a non-empty string
    # with no page behind it, and it used to pass straight through to `verified`.
    if body.proof_status == "verified" and not proofcheck.looks_openable(application["proof_url"]):
        raise HTTPException(409, "no_proof_to_check")
    # A rejection that does not say why is a dead end for the applicant and for
    # whoever picks the case up next, so the reason is required rather than
    # optional. "other" is the escape hatch, and it demands the note instead.
    if body.proof_status == "rejected":
        if body.reason not in REJECTION_REASONS:
            raise HTTPException(422, "unknown_rejection_reason")
        if body.reason == "other" and not body.note.strip():
            raise HTTPException(422, "other_needs_a_note")
    conn.execute("UPDATE athlete_applications SET proof_status = ?, review_reason = ?,"
                 " review_note = ?, reviewed_by = ? WHERE id = ?",
                 (body.proof_status, body.reason, body.note.strip(), user["id"], application_id))
    # The second way out of a freeze: a reviewer opened their proof and it held.
    # The first is redeeming a fresh club link. Nothing else clears it.
    if body.proof_status == "verified":
        conn.execute("UPDATE athlete_profiles SET frozen_at = NULL, frozen_by_club = NULL"
                     " WHERE id = ?", (application["athlete_id"],))
    application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?", (application_id,))
    profile = row(conn, "SELECT * FROM athlete_profiles WHERE id = ?",
                  (application["athlete_id"],))
    log_event(conn, "user", "admission.proof_checked", "athlete", profile["id"],
              {"application_id": application_id, "proof_status": body.proof_status,
               "source": "admin", "reviewer": user["id"]})
    via = "club_nomination" if application["nominated_by_club"] else "self"
    verdict = _evaluate(conn, application, profile, via=via)

    # Tell the applicant. Composed here, where the decision and its reason are
    # both in hand, and queued rather than sent -- see `queue_email`.
    if body.proof_status in ("verified", "rejected"):
        queue_email(conn, profile, decision=verdict, proof_status=body.proof_status,
                    reason=body.reason, note=body.note.strip())
    conn.commit()
    return verdict


def queue_email(conn, profile: dict, *, decision: dict, proof_status: str,
                reason: str, note: str) -> None:
    """Write the message the applicant is owed into the outbox.

    Nothing is sent. There is no mail provider wired up, and a function that
    claimed to send while doing nothing would be the one lie in an admission
    trail whose whole point is that every step is auditable. The row records
    exactly what would go out, a reviewer can read it back, and attaching a
    provider later means draining this table rather than rewriting this call.
    """
    account = row(conn, "SELECT id, email, display_name FROM users WHERE id = ?",
                  (profile["user_id"],)) if profile["user_id"] else None
    if account is None:
        return          # an unclaimed profile has nobody to write to

    name = account["display_name"]
    listed = decision.get("listing") == "listed"
    if proof_status == "verified" and listed:
        subject = "Your Stride profile is live"
        lines = [
            f"Hi {name},",
            "We checked the page you linked, found your name on it, and your profile is now"
            " listed in the athlete directory.",
            "Sponsors can see your marketability score and make you offers, and you can post"
            " to your wall whenever you like.",
        ]
    elif proof_status == "verified":
        subject = "Your proof checked out"
        lines = [
            f"Hi {name},",
            "We found your name on the page you linked.",
            "Your profile is not listed yet because there is no analytics behind it. Connect"
            " a platform and it goes live on the next sync.",
        ]
    else:
        subject = "About your Stride application"
        lines = [
            f"Hi {name},",
            "We looked at the proof link on your application and could not accept it."
            + (" " + REJECTION_REASONS[reason] if REJECTION_REASONS.get(reason) else ""),
            "You can submit a different link at any time. A page a stranger can open, with"
            " your name on it, is all we need.",
        ]
    if note:
        lines.append("From the reviewer:\n" + note)
    lines.append("-- Stride")
    body = "\n\n".join(lines)

    conn.execute("INSERT INTO email_outbox (to_email, to_user_id, subject, body, kind,"
                 " created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (account["email"], account["id"], subject, body,
                  f"admission.{proof_status}", now_iso()))
    notify(conn, account["id"], f"admission.{proof_status}", subject, lines[1][:140],
           "/athlete/application")


# -- club invite links -------------------------------------------------------
#
# A verified club can onboard its own athletes without each of them waiting in
# the proof queue. The link is the club saying "this person is ours", which is
# the same thing a reviewer would have been checking on a roster page, so it
# replaces **the proof check** -- and only that.
#
# It is not a bypass of admission. The athlete still states their own
# competition level and date of birth, because a club cannot supply either, and
# the 16+ gate is not something a third party gets to clear on somebody else's
# behalf. Links are single-use and bounded by the roster the club declared, so a
# leaked link onboards one person, and minting a thousand athletes still costs a
# thousand declared roster places.

INVITE_TTL_DAYS = 14


def _club_is_verified(conn, club_id: int) -> bool:
    app = row(conn, "SELECT decision FROM club_applications WHERE club_id = ?", (club_id,))
    return app is not None and app["decision"] == "verified"


def _link_state(link: dict) -> str:
    if link["revoked_at"]:
        return "revoked"
    if link["redeemed_at"]:
        return "redeemed"
    if link["expires_at"] < now_iso():
        return "expired"
    return "open"


class InviteLinkIn(BaseModel):
    """Who the link is for, in the club's own words.

    A token is deliberately unreadable, so a club holding four open links had no
    way to tell which one it had emailed to whom — and so no way to revoke the
    right one. Free text rather than a validated email because a club may key it
    by shirt number, agent, or trial date; it is a note to itself, and the
    product should not have an opinion about the format of somebody's own notes.
    """
    label: str = Field("", max_length=120)


@router.post("/club/invite-links", status_code=201)
def create_invite_link(body: InviteLinkIn | None = None,
                       user: dict = Depends(require_role("club")),
                       conn: sqlite3.Connection = Depends(get_db)):
    club = _own_club(conn, user)
    # Same lock-before-read as nominations, and for the same reason: two
    # requests that each read the old count both find room in the budget.
    lock_for_update(conn, "club_applications", "club_id", club["id"])
    if not _club_is_verified(conn, club["id"]):
        raise HTTPException(403, "club_not_verified")

    declared = row(conn, "SELECT registered_athletes FROM club_applications WHERE club_id = ?",
                   (club["id"],))["registered_athletes"] or 0
    spent = row(conn, "SELECT COUNT(*) AS n FROM club_invite_links WHERE club_id = ?"
                      " AND revoked_at IS NULL", (club["id"],))["n"]
    if spent >= declared:
        raise HTTPException(409, "roster_budget_exhausted")

    token = secrets.token_urlsafe(24)
    expires = (datetime.now(timezone.utc) + timedelta(days=INVITE_TTL_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    label = (body.label if body else "").strip()
    conn.execute("INSERT INTO club_invite_links (club_id, token, label, created_at, expires_at)"
                 " VALUES (?, ?, ?, ?, ?)", (club["id"], token, label, now_iso(), expires))
    log_event(conn, "user", "club.invite_link_created", "club", club["id"],
              {"expires_at": expires, "labelled": bool(label)})
    conn.commit()
    return {"token": token, "label": label, "expires_at": expires,
            "remaining": declared - spent - 1}


@router.get("/club/invite-links")
def list_invite_links(user: dict = Depends(require_role("club")),
                      conn: sqlite3.Connection = Depends(get_db)):
    club = _own_club(conn, user)
    out = []
    for link in rows(conn, "SELECT * FROM club_invite_links WHERE club_id = ?"
                           " ORDER BY id DESC", (club["id"],)):
        athlete = row(conn, "SELECT slug, display_name, frozen_at FROM athlete_profiles"
                            " WHERE id = ?", (link["redeemed_by"],)) if link["redeemed_by"] else None
        out.append({"id": link["id"], "token": link["token"], "state": _link_state(link),
                    "label": link["label"], "created_at": link["created_at"],
                    "expires_at": link["expires_at"], "redeemed_at": link["redeemed_at"],
                    "athlete": dict(athlete) if athlete else None})
    return out


@router.post("/club/invite-links/{link_id}/revoke")
def revoke_invite_link(link_id: int, user: dict = Depends(require_role("club")),
                       conn: sqlite3.Connection = Depends(get_db)):
    """Withdraw the vouching, and freeze whoever it admitted.

    The club is the only evidence behind a link-admitted athlete, so withdrawing
    it has to take the listing with it -- otherwise a club could onboard anybody,
    walk away, and leave a profile standing on nothing. Frozen rather than
    deleted: the athlete keeps their account and everything they published, and
    has two ways back.
    """
    club = _own_club(conn, user)
    link = row(conn, "SELECT * FROM club_invite_links WHERE id = ? AND club_id = ?",
               (link_id, club["id"]))
    if link is None:
        raise HTTPException(404, "unknown_invite_link")
    if link["revoked_at"]:
        raise HTTPException(409, "already_revoked")

    conn.execute("UPDATE club_invite_links SET revoked_at = ? WHERE id = ?", (now_iso(), link_id))
    froze = None
    if link["redeemed_by"]:
        athlete = row(conn, "SELECT * FROM athlete_profiles WHERE id = ?", (link["redeemed_by"],))
        conn.execute("UPDATE athlete_profiles SET status = 'draft', frozen_at = ?,"
                     " frozen_by_club = ? WHERE id = ?", (now_iso(), club["id"], athlete["id"]))
        log_event(conn, "user", "athlete.frozen", "athlete", athlete["id"],
                  {"club_id": club["id"], "link_id": link_id})
        if athlete["user_id"]:
            notify(conn, athlete["user_id"], "frozen",
                   f"{club['name']} withdrew their invitation",
                   "Your profile is out of the directory. A new link from a club puts it"
                   " back, or you can submit a proof link of your own.",
                   "/athlete/application")
        froze = athlete["slug"]
    log_event(conn, "user", "club.invite_link_revoked", "club", club["id"],
              {"link_id": link_id, "froze": froze})
    conn.commit()
    return {"ok": True, "froze": froze}


class RedeemIn(ApplicationIn):
    """The application form minus the proof -- the club supplies that half."""


@router.post("/athlete/invite-links/{token}/redeem")
def redeem_invite_link(token: str, body: RedeemIn,
                       user: dict = Depends(require_role("athlete")),
                       conn: sqlite3.Connection = Depends(get_db)):
    profile = _own_athlete(conn, user)
    link = row(conn, "SELECT * FROM club_invite_links WHERE token = ?", (token,))
    if link is None:
        raise HTTPException(404, "unknown_invite_link")
    state = _link_state(link)
    if state != "open":
        raise HTTPException(409, "link_" + state)
    club = row(conn, "SELECT * FROM clubs WHERE id = ?", (link["club_id"],))
    if not _club_is_verified(conn, club["id"]):
        # verification can be withdrawn between issuing a link and redeeming it
        raise HTTPException(403, "club_not_verified")

    club_app = row(conn, "SELECT roster_url FROM club_applications WHERE club_id = ?",
                   (club["id"],))
    fields = body.model_dump()
    fields["proof_kind"] = "roster"
    fields["proof_url"] = club_app["roster_url"] if club_app else ""

    columns = ("discipline", "club_name", "league_name", "competition_level",
               "years_competing", "birth_year", "proof_url", "proof_kind")
    values = tuple(fields[c] for c in columns)
    existing = row(conn, "SELECT * FROM athlete_applications WHERE athlete_id = ?",
                   (profile["id"],))
    if existing:
        conn.execute("UPDATE athlete_applications SET "
                     + ", ".join(c + " = ?" for c in columns)
                     + ", proof_status = 'verified', nominated_by_club = ?, submitted_at = ?"
                       " WHERE id = ?", values + (club["id"], now_iso(), existing["id"]))
    else:
        conn.execute("INSERT INTO athlete_applications (athlete_id, "
                     + ", ".join(columns)
                     + ", proof_status, nominated_by_club, submitted_at) VALUES (?, "
                     + ", ".join("?" for _ in columns) + ", 'verified', ?, ?)",
                     (profile["id"],) + values + (club["id"], now_iso()))

    # The link is spent whether or not the athlete clears the gate: a roster
    # place is consumed by the attempt, which is what makes the budget mean
    # anything at all.
    conn.execute("UPDATE club_invite_links SET redeemed_by = ?, redeemed_at = ? WHERE id = ?",
                 (profile["id"], now_iso(), link["id"]))
    # a fresh vouching clears an old freeze -- one of the two ways back in
    conn.execute("UPDATE athlete_profiles SET frozen_at = NULL, frozen_by_club = NULL"
                 " WHERE id = ?", (profile["id"],))
    log_event(conn, "user", "club.invite_link_redeemed", "athlete", profile["id"],
              {"club_id": club["id"], "link_id": link["id"]})

    application = row(conn, "SELECT * FROM athlete_applications WHERE athlete_id = ?",
                      (profile["id"],))
    profile = row(conn, "SELECT * FROM athlete_profiles WHERE id = ?", (profile["id"],))
    verdict = _evaluate(conn, application, profile, via="club_nomination")
    conn.commit()
    return verdict


@router.get("/admin/club-rejection-reasons")
def club_rejection_reasons(_: dict = Depends(require_role("admin"))):
    """The club reviewer's dropdown, served for the same reason as the athlete
    one: a second copy in the client drifts, and the copy that drifts is the
    one somebody is reading."""
    return [{"value": k, "label": v or "Something else — say what in the note"}
            for k, v in CLUB_REJECTION_REASONS.items()]


@router.get("/admin/rejection-reasons")
def rejection_reasons(_: dict = Depends(require_role("admin"))):
    """The reviewer's dropdown, served rather than duplicated in the client.

    Two copies of this list drift, and the copy that drifts is always the one
    the reviewer sees, so a reason the server refuses is offered in the UI.
    """
    return [{"value": k, "label": v or "Something else — say what in the note"}
            for k, v in REJECTION_REASONS.items()]


@router.get("/admin/outbox")
def outbox(limit: int = Query(30, ge=1, le=200),
           _: dict = Depends(require_role("admin")),
           conn: sqlite3.Connection = Depends(get_db)):
    """What the product owes people, and has not sent.

    `sent_at` stays null until a mail provider is attached. Showing the queue
    is the honest version of "an email was sent": a reviewer can read the exact
    text an applicant would receive, and nobody has to trust a claim.
    """
    return [{"id": e["id"], "to": e["to_email"], "subject": e["subject"], "body": e["body"],
             "kind": e["kind"], "at": e["created_at"], "sent": e["sent_at"] is not None}
            for e in rows(conn, "SELECT * FROM email_outbox ORDER BY id DESC LIMIT ?", (limit,))]


def _auto_check(conn, *, url: str, name: str, fetcher=None) -> proofcheck.ProofResult:
    return proofcheck.check(url, name, fetcher or proofcheck.fetch)


@router.post("/admin/applications/{application_id}/auto-check")
def auto_check_application(application_id: int,
                           user: dict = Depends(require_role("admin")),
                           conn: sqlite3.Connection = Depends(get_db)):
    """Open the applicant's link and decide, where the answer is unambiguous.

    Deliberately a separate endpoint rather than something that runs on submit:
    a network fetch on a user's request path buys them a six-second wait for a
    result they cannot act on, and it puts the SSRF surface on an unauthenticated
    form. A cron or an ops sweep calls this; anything it cannot conclude stays
    exactly where it was, in the human queue.
    """
    application = row(conn, "SELECT ap.*, a.display_name FROM athlete_applications ap"
                      " JOIN athlete_profiles a ON a.id = ap.athlete_id WHERE ap.id = ?",
                      (application_id,))
    if application is None:
        raise HTTPException(404, "unknown_application")
    if application["proof_status"] == "rejected":
        # a failed check is a finding about the applicant; a crawler does not
        # get to clear it, only a reviewer does
        raise HTTPException(409, "proof_already_rejected")

    result = _auto_check(conn, url=application["proof_url"],
                         name=application["display_name"])
    log_event(conn, "system", "admission.proof_checked", "athlete", application["athlete_id"],
              {"application_id": application_id, "source": "auto",
               "outcome": result.status, "reason": result.reason,
               "matched": result.matched, "url": application["proof_url"]})
    if not result.conclusive:
        conn.commit()
        return {"checked": False, "reason": result.reason, "detail": result.detail,
                "decision": application["decision"]}

    conn.execute("UPDATE athlete_applications SET proof_status = 'verified' WHERE id = ?",
                 (application_id,))
    application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?", (application_id,))
    profile = row(conn, "SELECT * FROM athlete_profiles WHERE id = ?",
                  (application["athlete_id"],))
    via = "club_nomination" if application["nominated_by_club"] else "self"
    verdict = _evaluate(conn, application, profile, via=via)
    return {"checked": True, "reason": result.reason, "detail": result.detail, **verdict}


@router.post("/admin/auto-check")
def auto_check_queue(limit: int = Query(25, le=100),
                     user: dict = Depends(require_role("admin")),
                     conn: sqlite3.Connection = Depends(get_db)):
    """Sweep the queue. Reports what it could not conclude as well as what it
    could — a sweep that only counted its successes would make the queue look
    like it was emptying when it was not."""
    queued = rows(conn, """
        SELECT ap.id, ap.proof_url, ap.athlete_id, a.display_name
        FROM athlete_applications ap JOIN athlete_profiles a ON a.id = ap.athlete_id
        WHERE ap.decision = 'review' AND ap.proof_status = 'pending'
        ORDER BY ap.id LIMIT ?""", (limit,))
    verified, inconclusive = [], {}
    for item in queued:
        result = _auto_check(conn, url=item["proof_url"], name=item["display_name"])
        log_event(conn, "system", "admission.proof_checked", "athlete", item["athlete_id"],
                  {"application_id": item["id"], "source": "auto",
                   "outcome": result.status, "reason": result.reason})
        if not result.conclusive:
            inconclusive[result.reason] = inconclusive.get(result.reason, 0) + 1
            continue
        conn.execute("UPDATE athlete_applications SET proof_status = 'verified' WHERE id = ?",
                     (item["id"],))
        application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?", (item["id"],))
        profile = row(conn, "SELECT * FROM athlete_profiles WHERE id = ?", (item["athlete_id"],))
        _evaluate(conn, application, profile,
                  via="club_nomination" if application["nominated_by_club"] else "self")
        verified.append(item["id"])
    conn.commit()
    return {"considered": len(queued), "verified": len(verified),
            "still_for_a_human": inconclusive}


@router.post("/admin/clubs/{club_id}/proof")
def set_club_proof(club_id: int, body: ProofIn,
                   user: dict = Depends(require_role("admin")),
                   conn: sqlite3.Connection = Depends(get_db)):
    """Record the outcome of checking a club's roster page, then re-decide.

    The counterpart of the athlete endpoint above, and without it there is no
    route to a verified club at all: a club re-submitting its own form resets
    the proof to `pending` by design, so the only way the status can move
    forward is a reviewer moving it.
    """
    if body.proof_status not in PROOF_STATUSES:
        raise HTTPException(422, "unknown_proof_status")
    application = row(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club_id,))
    if application is None:
        raise HTTPException(404, "unknown_club_application")
    if body.proof_status == "verified" and not proofcheck.looks_openable(application["roster_url"]):
        raise HTTPException(409, "no_proof_to_check")
    # Same rule as the athlete side, and for the same reason: "rejected" with no
    # reason is a dead end for the club and for the next reviewer to open it.
    if body.proof_status == "rejected":
        if body.reason not in CLUB_REJECTION_REASONS:
            raise HTTPException(422, "unknown_rejection_reason")
        if body.reason == "other" and not body.note.strip():
            raise HTTPException(422, "other_needs_a_note")
    application = {**application, "proof_status": body.proof_status}
    scored = club_legitimacy(application)
    conn.execute("UPDATE club_applications SET proof_status = ?, legitimacy = ?,"
                 " decision = ?, policy_version = ?, decided_at = ? WHERE club_id = ?",
                 (body.proof_status, scored["legitimacy"], scored["decision"],
                  POLICY_VERSION, now_iso(), club_id))
    log_event(conn, "user", "club.proof_checked", "club", club_id,
              {"proof_status": body.proof_status, "legitimacy": scored["legitimacy"],
               "decision": scored["decision"], "reviewer": user["id"],
               "reason": body.reason})
    if body.proof_status in ("verified", "rejected"):
        queue_club_email(conn, club_id, decision=scored["decision"],
                         proof_status=body.proof_status, reason=body.reason,
                         note=body.note.strip())
    conn.commit()
    return scored


def queue_club_email(conn, club_id: int, *, decision: str, proof_status: str,
                     reason: str, note: str) -> None:
    """The club's half of "tell them what was decided and why".

    Queued, not sent, for the same reason as the athlete one: there is no mail
    provider, and a call that claimed to deliver would be the only unverifiable
    step in a trail built to be verifiable.
    """
    club = row(conn, "SELECT id, name, user_id FROM clubs WHERE id = ?", (club_id,))
    if club is None or not club["user_id"]:
        return
    account = row(conn, "SELECT id, email, display_name FROM users WHERE id = ?",
                  (club["user_id"],))
    if account is None:
        return

    if proof_status == "verified":
        subject = f"{club['name']} is verified on Stride"
        lines = [
            f"Hi {account['display_name']},",
            "We checked your roster page and verified the club.",
            "You can now invite athletes with a link that skips the proof queue, and nominate"
            " athletes who apply on their own. Both are bounded by the roster size you"
            " declared.",
        ]
    else:
        subject = f"About {club['name']}'s verification"
        lines = [
            f"Hi {account['display_name']},",
            "We looked at the roster page on your application and could not verify the club."
            + (" " + CLUB_REJECTION_REASONS[reason] if CLUB_REJECTION_REASONS.get(reason) else ""),
            "You can update the application and submit a different page at any time.",
        ]
    if note:
        lines.append("From the reviewer:" + chr(10) + note)
    lines.append("-- Stride")

    conn.execute("INSERT INTO email_outbox (to_email, to_user_id, subject, body, kind,"
                 " created_at) VALUES (?, ?, ?, ?, ?, ?)",
                 (account["email"], account["id"], subject,
                  (chr(10) * 2).join(lines), f"club.{proof_status}", now_iso()))
    notify(conn, account["id"], f"club.{proof_status}", subject, lines[1][:140],
           "/club/eligibility")


@router.post("/admin/clubs/{club_id}/revoke")
def revoke_club(club_id: int, user: dict = Depends(require_role("admin")),
                conn: sqlite3.Connection = Depends(get_db)):
    """De-verify a club and withdraw what its nominations were holding up.

    Only athletes who *depended* on the nomination move: anyone whose own
    credibility already cleared the admit threshold keeps their place, because
    the club was never what got them in. They land in review, not rejected —
    losing your supporting evidence is not the same as being caught lying.
    """
    club_app = row(conn, "SELECT * FROM club_applications WHERE club_id = ?", (club_id,))
    if club_app is None:
        raise HTTPException(404, "unknown_club_application")
    conn.execute("UPDATE club_applications SET decision = 'rejected', decided_at = ?"
                 " WHERE club_id = ?", (now_iso(), club_id))

    dependent = rows(conn, "SELECT * FROM athlete_applications WHERE nominated_by_club = ?"
                     " AND decision = 'admitted' AND (credibility IS NULL OR credibility < ?)",
                     (club_id, ADMIT_AT))
    for application in dependent:
        conn.execute(
            "UPDATE athlete_applications SET decision = 'review',"
            " decision_rule = 'club_verification_revoked', admitted_via = '', decided_at = ?"
            " WHERE id = ?", (now_iso(), application["id"]))
        conn.execute("UPDATE athlete_profiles SET status = 'draft' WHERE id = ?",
                     (application["athlete_id"],))
    log_event(conn, "user", "club.verification_revoked", "club", club_id,
              {"reviewer": user["id"], "athletes_returned_to_review": len(dependent),
               "athlete_ids": [a["athlete_id"] for a in dependent]})
    conn.commit()
    return {"club_id": club_id, "decision": "rejected",
            "athletes_returned_to_review": len(dependent)}
