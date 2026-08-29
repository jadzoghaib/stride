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

import sqlite3
from datetime import datetime
from statistics import median

from creatorlens.analytics.scoring import latest_score
from creatorlens.events import log_event
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..admission import (ADMIT_AT, COMPETITION_LEVELS, DISQUALIFYING_RULES,
                         PROOF_KINDS, PROOF_STATUSES,
                         POLICY_VERSION, admission_decision, age_from,
                         athlete_credibility, club_legitimacy)
from ..auth import get_db, require_role
from .. import proofcheck
from ..db import lock_for_update, now_iso, row, rows

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
        age=age_from(application["birth_year"]),
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
    granted = admitted and bool(profile["creatorlens_creator_id"])
    listing = "listed" if granted else "draft"
    if listing == "draft" and not may_delist:
        listing = profile["status"]

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
         (via if granted else ""), POLICY_VERSION, now_iso(), application["id"]))
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
    birth_year: int | None = Field(default=None, ge=1930, le=2030)
    proof_url: str = Field(default="", max_length=500)
    proof_kind: str = Field(default="none", max_length=20)


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
              body.years_competing, body.birth_year, body.proof_url, body.proof_kind,
              proof_status)
    if existing:
        conn.execute(
            "UPDATE athlete_applications SET discipline = ?, club_name = ?, league_name = ?,"
            " competition_level = ?, years_competing = ?, birth_year = ?, proof_url = ?,"
            " proof_kind = ?, proof_status = ? WHERE id = ?", (*fields, existing["id"]))
        application_id = existing["id"]
    else:
        cur = conn.execute(
            "INSERT INTO athlete_applications (athlete_id, discipline, club_name, league_name,"
            " competition_level, years_competing, birth_year, proof_url, proof_kind,"
            " proof_status, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
    return {"application": application, "scored": scored,
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


class ProofIn(BaseModel):
    proof_status: str


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
    conn.execute("UPDATE athlete_applications SET proof_status = ? WHERE id = ?",
                 (body.proof_status, application_id))
    application = row(conn, "SELECT * FROM athlete_applications WHERE id = ?", (application_id,))
    profile = row(conn, "SELECT * FROM athlete_profiles WHERE id = ?",
                  (application["athlete_id"],))
    log_event(conn, "user", "admission.proof_checked", "athlete", profile["id"],
              {"application_id": application_id, "proof_status": body.proof_status,
               "source": "admin", "reviewer": user["id"]})
    via = "club_nomination" if application["nominated_by_club"] else "self"
    return _evaluate(conn, application, profile, via=via)


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
    application = {**application, "proof_status": body.proof_status}
    scored = club_legitimacy(application)
    conn.execute("UPDATE club_applications SET proof_status = ?, legitimacy = ?,"
                 " decision = ?, policy_version = ?, decided_at = ? WHERE club_id = ?",
                 (body.proof_status, scored["legitimacy"], scored["decision"],
                  POLICY_VERSION, now_iso(), club_id))
    log_event(conn, "user", "club.proof_checked", "club", club_id,
              {"proof_status": body.proof_status, "legitimacy": scored["legitimacy"],
               "decision": scored["decision"], "reviewer": user["id"]})
    conn.commit()
    return scored


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
