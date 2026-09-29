"""Screenshot the deployed demo for the product appendix.

    uv run --with playwright python business-plan/make_ui_shots.py

Uses the system Chrome (`channel="chrome"`) rather than Playwright's own
download, which this machine does not have and which is a 130MB fetch to avoid.

The container sleeps, so the first navigation pays about forty seconds. Every
timeout here is set for that rather than for a warm server.

Each shot is a real screen with the seeded demo data behind it. Nothing here is
a mockup, which is the point of including them: the plan claims a working
product exists, and this is the evidence for that claim.
"""

from __future__ import annotations

import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "https://stride-demo.onrender.com"
OUT = pathlib.Path(__file__).parent / "attachments" / "ui"
PASSWORD = "stride123"

# (filename, role email or None for signed out, path, short title, caption)
# The title and the caption are separate because the appendix uses both: the
# title is a heading, the caption is the sentence under the image. Deriving one
# from the other printed the same sentence three times per screen.
SHOTS = [
    ("01-sign-in", None, "/auth", "Sign in",
     "Five seeded roles, one per side of the marketplace, open to anyone."),
    ("02-athlete-dashboard", "athlete@demo.stride", "/athlete", "Athlete dashboard",
     "The marketability score and its ranked dimensions, computed from connected "
     "platform data rather than self-reported."),
    # Captured signed out on purpose: this is the public view, and the API
    # withholds the score and audience detail from it. The caption used to
    # promise what a sponsor sees, which is a different and richer screen.
    ("03-athlete-public", None, "/athletes/kaia-mercer", "Public athlete profile",
     "The public profile, seen signed out. Identity, sport and club are open; "
     "the score and audience breakdown are withheld until a viewer is known."),
    ("04-sponsor-campaigns", "sponsor@demo.stride", "/sponsor", "Sponsor workspace",
     "Campaigns carry a brief, and the brief is what the matching engine scores "
     "against."),
    ("05-club-hq", "club@demo.stride", "/club", "Club HQ",
     "The roster is the club channel of the sales plan: one relationship carries "
     "twenty to forty athletes."),
    ("06-admin-review", "admin@demo.stride", "/admin/review", "Admission queue",
     "The operations plan treats admission review as the only step consuming "
     "meaningful human time. This is that step."),
]


def sign_in(page, email: str) -> None:
    page.goto(f"{BASE}/auth", timeout=180_000, wait_until="domcontentloaded")
    page.wait_for_selector("input[type=password]", timeout=120_000)
    boxes = page.locator("input")
    boxes.nth(0).fill(email)
    page.locator("input[type=password]").fill(PASSWORD)
    # `get_by_role("button", name="Sign in")` matches two things: the mode tab
    # and the form's own submit. Target the submit by its class, which only the
    # primary action carries.
    page.locator("form button.btn-go").first.click()
    page.wait_for_url(lambda u: "/auth" not in u, timeout=120_000)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name, email, path, _title, _caption in SHOTS:
            ctx = browser.new_context(viewport={"width": 1440, "height": 1000},
                                      device_scale_factor=2)
            page = ctx.new_page()
            try:
                if email:
                    sign_in(page, email)
                page.goto(f"{BASE}{path}", timeout=180_000,
                          wait_until="domcontentloaded")
                # The shell renders before its data arrives, so a screenshot
                # taken on navigation alone captures skeletons.
                try:
                    page.wait_for_load_state("networkidle", timeout=45_000)
                except Exception:
                    pass
                page.wait_for_timeout(2500)

                # A networkidle timeout is not evidence the data arrived, and
                # saving anyway is how a loading state ends up in the appendix
                # looking like the product. Refuse the shot instead.
                body = page.inner_text("body")
                if any(tell in body for tell in ("Loading…", "Loading...")):
                    raise RuntimeError("page still showing a loading state")
                if len(body.split()) < 40:
                    raise RuntimeError(f"page looks empty ({len(body.split())} words)")

                target = OUT / f"{name}.png"
                page.screenshot(path=str(target))
                written.append(name)
                print(f"  {name:22} {target.stat().st_size // 1024:5} KB")
            except Exception as exc:  # one bad screen must not lose the rest
                print(f"  {name:22} FAILED: {str(exc)[:90]}", file=sys.stderr)
            finally:
                ctx.close()
        browser.close()
    print(f"{len(written)} of {len(SHOTS)} captured -> {OUT}")
    return 0 if len(written) == len(SHOTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
