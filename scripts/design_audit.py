"""Does the UI code still honour DESIGN.md? Measured, not eyeballed.

    python scripts/design_audit.py

The brief says "Measure, don't eyeball" about contrast and "set a type scale
and stay on it" about type. Both are checkable, and both had drifted before
anyone checked: a chart category was painted in a colour byte-identical to the
light-mode accent and measured 2.16:1 on white, and 57 arbitrary `text-[Npx]`
values were spread across 25 files with no scale written down anywhere.

What fails a run:

  * a semantic colour under 4.5:1 on `panel`, in either theme -- including on
    a 10% tint of itself, which is the surface chips actually paint it on
  * `warn` and `accent` too close to tell apart, the one rule the palette
    exists to protect
  * a hard-coded colour that duplicates a token's value, which will drift the
    first time the token changes
  * an arbitrary `text-[Npx]`, now that the scale has names
  * a pattern the brief explicitly rejects

Decorative literals are allowed and listed by name below, with the reason.
Anything not on that list is a finding.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "apps/web/src"

#: Colours written as literals on purpose. Each is decoration rather than text,
#: or a foreground whose surface never changes with the theme.
ALLOWED_LITERALS = {
    "components/content.tsx": "gradient stops on the locked panel — texture behind a blur, no text on them",
    "components/Cover.tsx": "a 9%-alpha white stroke on generated cover art, over the art's own ground",
    "components/ui.tsx": "text on a coloured avatar circle: the fill is generated, not a token",
}


#: Tokens that appear as *text on a 10% wash of themselves* -- the chip
#: surface. Those cost ~1.3-1.6 points of contrast, so they are measured
#: there as well as on the panel. The others are not: `ink-3` is body text on
#: the panel and `cat-*` are chart fills, and measuring them on a tint they
#: never touch is how this script's first run produced two findings that were
#: about the script rather than the product.
ON_OWN_TINT = ("ok", "warn", "critical", "accent-ink",
               "plat-instagram", "plat-tiktok", "plat-youtube")


def strip_comments(text: str) -> list[tuple[int, str]]:
    """Numbered lines with comment bodies blanked.

    `.stride-main` carries the sentence "Deliberately not `width: 100vw`",
    which is the codebase agreeing with the rule -- and the first version of
    this script reported it as a violation of it.
    """
    out, in_block = [], False
    for ln, line in enumerate(text.splitlines(), 1):
        kept = []
        i = 0
        while i < len(line):
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    i = len(line)
                else:
                    in_block, i = False, end + 2
            elif line.startswith("//", i) or line.startswith("*", i) and not kept:
                break
            elif line.startswith("/*", i):
                in_block, i = True, i + 2
            else:
                kept.append(line[i])
                i += 1
        out.append((ln, "".join(kept)))
    return out


def lum(rgb: tuple[int, int, int]) -> float:
    def ch(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def blend(fg: tuple[int, int, int], bg: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return tuple(round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg))  # type: ignore[return-value]


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def tokens(block: str) -> dict[str, tuple[int, int, int]]:
    return {m.group(1): (int(m.group(2)), int(m.group(3)), int(m.group(4)))
            for m in re.finditer(r"--c-([a-z0-9-]+):\s*(\d+)\s+(\d+)\s+(\d+);", block)}


def main() -> int:
    css = (SRC / "index.css").read_text(encoding="utf-8")
    dark = tokens(css[css.index(":root {"):css.index(":root[data-theme='light']")])
    light = tokens(css[css.index(":root[data-theme='light']"):css.index("@layer base")])
    findings: list[str] = []

    # ── 1. contrast, both themes, on the panel and on a tint of itself ───────
    print("== semantic colours on `panel` (>= 4.5:1, both themes) ==")
    for name, T in (("dark", dark), ("light", light)):
        for tok in ("ink", "ink-2", "ink-3", "accent-ink", "ok", "warn", "critical",
                    "cat-1", "cat-2", "cat-3", "plat-instagram", "plat-tiktok", "plat-youtube"):
            if tok not in T:
                findings.append(f"token --c-{tok} missing from the {name} palette")
                continue
            flat = contrast(T[tok], T["panel"])
            if tok in ON_OWN_TINT:
                tinted = contrast(T[tok], blend(T[tok], T["panel"], 0.10))
                worst, shown = min(flat, tinted), f"on its 10% tint {tinted:5.2f}"
            else:
                worst, shown = flat, "(panel only)"
            flag = "" if worst >= 4.5 else "   <-- UNDER AA"
            if flag:
                findings.append(f"{name} --c-{tok} is {worst:.2f}:1 where it is used")
            print(f"  {name:5} {tok:15} panel {flat:5.2f}   {shown}{flag}")

    # ── 2. the one rule the palette exists to protect ────────────────────────
    print("\n== `warn` is distinguishable from `accent` ==")
    for name, T in (("dark", dark), ("light", light)):
        distance = sum(abs(a - b) for a, b in zip(T["warn"], T["accent"]))
        print(f"  {name:5} channel distance {distance:4d}")
        if distance <= 60:
            findings.append(f"{name}: warn and accent are {distance} apart — indistinguishable")

    # ── 3. colours written outside the token layer ───────────────────────────
    print("\n== hard-coded colours ==")
    by_token = {v: f"--c-{k}" for k, v in dark.items()} | {v: f"light --c-{k}" for k, v in light.items()}
    literals = 0
    for f in sorted(SRC.rglob("*.ts*")):
        rel = f.relative_to(SRC).as_posix()
        for ln, line in strip_comments(f.read_text(encoding="utf-8")):
            for h in re.findall(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b", line):
                literals += 1
                if rel in ALLOWED_LITERALS:
                    continue     # decorative by declaration; the reason is beside the entry
                duplicate = by_token.get(hex_rgb(h))
                if duplicate:
                    findings.append(f"{rel}:{ln} hard-codes {h}, the value of {duplicate} — "
                                    "it will drift the first time that token changes")
                    print(f"  DRIFT {rel}:{ln} {h} == {duplicate}")
                else:
                    findings.append(f"{rel}:{ln} hard-codes {h} outside the token layer")
                    print(f"  LOOSE {rel}:{ln} {h}")
    allowed = ", ".join(sorted(ALLOWED_LITERALS))
    print(f"  {literals} literals seen; decorative ones allowed in: {allowed}")

    # ── 4. the type scale is named ───────────────────────────────────────────
    print("\n== the type scale ==")
    arbitrary_type: list[str] = []
    for f in sorted(SRC.rglob("*.ts*")) + [SRC / "index.css"]:
        for ln, line in strip_comments(f.read_text(encoding="utf-8")):
            for m in re.findall(r"text-\[(\d+)px\]", line):
                arbitrary_type.append(f"{f.relative_to(SRC).as_posix()}:{ln} text-[{m}px]")
    for hit in arbitrary_type:
        findings.append(f"{hit} — the scale has names; add one rather than a pixel value")
    print(f"  {len(arbitrary_type)} arbitrary `text-[Npx]` (want 0)")

    # ── 5. patterns the brief rejects ────────────────────────────────────────
    print("\n== patterns DESIGN.md rejects ==")
    rejected = {
        "rounded-2xl": r"\brounded-2xl\b",
        "rounded-xl": r"\brounded-xl\b",
        "gradient utility": r"\bbg-gradient-to-",
        # a word boundary: "Interest filters" is not the Inter typeface
        "Inter/Space Grotesk": r"\bInter\b(?!est)|Space Grotesk",
        "font CDN": r"fonts\.googleapis|fonts\.gstatic",
        # only as a width; `min(30rem, calc(100vw - 2rem))` is the correct use
        "width:100vw": r"width:\s*100vw|w-\[100vw\]",
        "emoji": r"[\U0001F300-\U0001FAFF]",
    }
    for label, pattern in rejected.items():
        hits = [f"{f.relative_to(SRC).as_posix()}:{ln}"
                for f in sorted(SRC.rglob("*.ts*")) + [SRC / "index.css"]
                for ln, line in strip_comments(f.read_text(encoding="utf-8"))
                if re.search(pattern, line)]
        print(f"  {label:22} {len(hits):3}  {', '.join(hits[:3])}")
        findings += [f"{label} at {h}" for h in hits]

    # ── 6. reduced motion ────────────────────────────────────────────────────
    guarded = "prefers-reduced-motion" in css
    print(f"\n== reduced motion ==\n  global guard present: {guarded}")
    if not guarded:
        findings.append("no prefers-reduced-motion guard in index.css")

    print("\n" + "-" * 74)
    if findings:
        print(f"{len(findings)} findings:")
        for f in findings[:40]:
            print("  -", f)
        return 1
    print("the UI still honours DESIGN.md: contrast measured, scale named, "
          "no rejected pattern, no colour loose outside the tokens.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
