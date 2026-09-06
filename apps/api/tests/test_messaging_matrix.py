"""Every ordered pair of roles, and whether one may open a thread with the other.

The rules live in `may_open` and were already covered case by case. What was
missing is the *matrix*: the pairs nobody thought to write a test for are
exactly the ones a permission bug hides in, because each individual test asserts
a door is open and none of them asserts which doors are shut.

The intended shape, stated once:

- **athlete, club and sponsor are an open network.** Any of the three may open
  with any of the three, with no prior relationship, because forming the
  relationship is what the message is for.
- **a fan reaches an athlete they subscribe to, and nobody else.** Not a club,
  not a sponsor, not another fan, and not an athlete they merely follow.
- **nobody cold-opens a thread with a fan** — including an athlete, who may
  answer their own subscribers but has no more business writing to a stranger's
  audience than a sponsor does.

That last clause is the one this file changed. `may_open` used to return True
for any athlete-initiated thread whatever the recipient, while its own docstring
said "an athlete may still answer their own audience". Answering was never the
question -- an existing thread is handled before `may_open` is consulted at all
-- so the code granted cold-opening and the comment described replying.
"""
from __future__ import annotations

import pytest

from conftest import MESSAGING_TABLES, preserved
from stride_api.db import row


@pytest.fixture(autouse=True)
def clean_slate(db):
    """Same isolation the rest of the messaging tests use, and for the sharper
    reason here: `may_open` is only consulted when no thread exists, so a
    conversation left behind by an earlier case turns a refusal into a 201 and
    the matrix quietly stops testing anything."""
    with preserved(db, MESSAGING_TABLES):
        yield

def _user_id(db, email: str) -> int:
    return row(db, "SELECT id FROM users WHERE email = ?", (email,))["id"]


def _send(client, to_user: int):
    return client.post("/api/messages", json={"to_user": to_user, "body": "Matrix probe"})


#: (sender fixture, recipient account, may open?) — the full working network
#: plus every way into and out of the audience.
MATRIX = [
    # the three that transact with each other: all nine pairs open
    ("athlete", "club@demo.stride", True),
    ("athlete", "sponsor@demo.stride", True),
    ("clubu", "athlete@demo.stride", True),
    ("clubu", "sponsor@demo.stride", True),
    ("sponsor", "athlete@demo.stride", True),
    ("sponsor", "club@demo.stride", True),

    # nobody cold-opens with an audience member
    ("clubu", "fan@demo.stride", False),
    ("sponsor", "fan@demo.stride", False),
    ("athlete", "fan@demo.stride", False),

    # and an audience member reaches only an athlete they pay for
    ("fan", "club@demo.stride", False),
    ("fan", "sponsor@demo.stride", False),
]


@pytest.mark.parametrize("sender_name,recipient_email,allowed", MATRIX)
def test_the_open_matrix(request, db, sender_name, recipient_email, allowed):
    sender = request.getfixturevalue(sender_name)
    r = _send(sender, _user_id(db, recipient_email))
    if allowed:
        assert r.status_code == 201, f"{sender_name} -> {recipient_email} should be allowed"
    else:
        assert r.status_code == 403, f"{sender_name} -> {recipient_email} should be refused"
        assert r.json()["detail"] == "cannot_message_this_person"


def test_a_fan_reaches_an_athlete_only_by_subscribing(fan, db):
    """Restates the rule this whole feature exists to enforce, from the matrix's
    point of view: the fan row is conditional where every other row is not."""
    kaia_user = _user_id(db, "athlete@demo.stride")
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE user_id = ?", (kaia_user,))["id"]

    # following is not subscribing, and the distinction is the revenue model
    fan.post(f"/api/follows/{kaia}")
    assert _send(fan, kaia_user).status_code == 403

    fan.post(f"/api/subscriptions/athlete/{kaia}")
    assert _send(fan, kaia_user).status_code == 201


def test_an_athlete_may_answer_a_subscriber_but_not_open_with_a_stranger(athlete, fan, db):
    """The asymmetry that makes the audience side safe.

    A fan who subscribes may write first, and the athlete may answer — reply
    rights come from the thread, so that works without any role granting it.
    What the athlete may not do is start the conversation with somebody who has
    not asked to hear from them.
    """
    fan_user = _user_id(db, "fan@demo.stride")
    assert _send(athlete, fan_user).status_code == 403, "no cold-open, even from an athlete"

    kaia_user = _user_id(db, "athlete@demo.stride")
    kaia = row(db, "SELECT id FROM athlete_profiles WHERE user_id = ?", (kaia_user,))["id"]
    fan.post(f"/api/subscriptions/athlete/{kaia}")
    assert _send(fan, kaia_user).status_code == 201, "the fan opens it"

    # and now the athlete can answer, because the thread exists
    assert _send(athlete, fan_user).status_code == 201
