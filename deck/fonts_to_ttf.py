"""Turn the app's self-hosted webfonts into TrueType the deck can use.

PowerPoint renders a font by name from what Windows has installed, and Barlow is
not a Windows font. The app ships it as woff2 under SIL Open Font License, which
permits redistribution and conversion, so the deck uses the same files the
product does rather than an approximation. Converted here, installed per user,
so the slides on the night are set in the typeface the screenshots are set in.
"""
import pathlib

from fontTools.ttLib import TTFont

SRC = pathlib.Path("../apps/web/public/fonts")
OUT = pathlib.Path("fonts")
OUT.mkdir(exist_ok=True)

for woff2 in sorted(SRC.glob("*.woff2")):
    font = TTFont(woff2)                 # fontTools reads woff2 directly
    font.flavor = None                   # drop the web wrapper: plain TTF
    name = font["name"]
    full = name.getDebugName(4) or woff2.stem
    family = name.getDebugName(1)
    target = OUT / f"{woff2.stem}.ttf"
    font.save(target)
    print(f"  {woff2.name:32} -> {target.name:34} family={family!r} full={full!r}")
print(f"\n{len(list(OUT.glob('*.ttf')))} TrueType files in {OUT.resolve()}")
