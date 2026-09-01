"""Generate `apps/web/src/components/countries.ts` — one SVG path per country.

The audience map used to be bubbles at country centroids over a single merged
land silhouette. A bubble encodes magnitude as area, which people read badly,
and it sits *on* a country rather than being one — so Germany and France, whose
centroids are 500km apart, overlapped into one blob at map scale.

A choropleth needs the countries as separate shapes, which the old `land.ts`
cannot provide: it is one path with every coastline merged into it. This script
writes the other thing — a lookup from ISO 3166-1 alpha-2 to a path string, in
the *same* equirectangular frame, so the two files can be drawn on top of each
other without re-projecting anything.

Run it when the projection changes or the source data is refreshed. It is not
part of the build: the output is committed, because a reader's own audience
breakdown should not depend on a CDN being up.

    uv run python scripts/build_country_paths.py

Sources, both fetched once and neither vendored:
  * world-atlas 110m countries (Natural Earth), keyed by ISO numeric
  * i18n-iso-countries codes.json, to turn numeric into alpha-2
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

TOPO = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"
CODES = "https://cdn.jsdelivr.net/npm/i18n-iso-countries@7.6.0/codes.json"

OUT = Path(__file__).resolve().parents[1] / "apps/web/src/components/countries.ts"

#: The projection `land.ts` is already in, and therefore the only one this may
#: use: x = (lon + 180) / 360, y = (78 - lat) / 150, over `CountryMap`'s own
#: 560x270 viewBox. The 78/150 crop drops the polar dead space nobody's audience
#: lives in. These two numbers must match the `W`/`H` in `charts.tsx`; if they
#: drift, the choropleth renders beside its own coastline instead of on it.
W, H = 560, 270


def fetch(url: str):
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.load(r)


def decode_arcs(topology: dict) -> list[list[tuple[float, float]]]:
    """TopoJSON stores arcs delta-encoded against a quantised grid."""
    sx, sy = topology["transform"]["scale"]
    tx, ty = topology["transform"]["translate"]
    out = []
    for arc in topology["arcs"]:
        x = y = 0
        points = []
        for dx, dy in arc:
            x += dx
            y += dy
            points.append((x * sx + tx, y * sy + ty))
        out.append(points)
    return out


def ring_points(arc_indices, arcs) -> list[tuple[float, float]]:
    """Stitch a ring out of arc references; a negative index means reversed."""
    points: list[tuple[float, float]] = []
    for idx in arc_indices:
        arc = arcs[~idx][::-1] if idx < 0 else arcs[idx]
        # the shared endpoint between consecutive arcs is stored once per arc
        points.extend(arc[1:] if points else arc)
    return points


def project(lon: float, lat: float) -> tuple[float, float]:
    return ((lon + 180.0) / 360.0 * W, (78.0 - lat) / 150.0 * H)


#: Points closer together than this are dropped. The map is 560 units wide and
#: renders into roughly 700 CSS pixels, so a third of a unit is well under half
#: a pixel -- detail below it cannot be seen and is only paid for. Natural Earth
#: 110m is already the coarsest tier published; this trims what remains.
MIN_STEP = 0.5


def _ring_area(points: list[tuple[float, float]]) -> float:
    """Shoelace, unsigned, in viewBox units."""
    a = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def to_path(rings: list[list[tuple[float, float]]]) -> str:
    """Projected, decimated and rounded to one decimal.

    Whole-unit rounding visibly facets a coastline at this size; a tenth of a
    unit does not, and combined with the `MIN_STEP` decimation it takes the
    generated file to roughly a third of its unfiltered size.

    The largest ring of a country is always kept, however small it is. Dropping
    rings under a threshold is what stops 174 countries carrying a few thousand
    invisible islets between them, but applied blindly it deletes Malta and
    Singapore *entirely* -- and a country with no shape cannot be shaded, so it
    would silently vanish from the map rather than merely lose an island.
    """
    projected = [[project(lon, lat) for lon, lat in ring] for ring in rings]
    biggest = max(range(len(projected)), key=lambda i: _ring_area(projected[i]))         if projected else -1

    parts = []
    for idx, ring in enumerate(projected):
        if idx != biggest and _ring_area(ring) < 0.6:
            continue
        drawn: list[str] = []
        last: tuple[float, float] | None = None
        for x, y in ring:
            if last is not None and abs(x - last[0]) < MIN_STEP and abs(y - last[1]) < MIN_STEP:
                continue
            pt = (round(x, 1), round(y, 1))
            if pt != last:
                drawn.append(f"{'M' if not drawn else 'L'}{pt[0]:g} {pt[1]:g}")
                last = pt
        if len(drawn) >= 3:
            parts.append("".join(drawn) + "Z")
    return "".join(parts)


def main() -> None:
    topology = fetch(TOPO)
    arcs = decode_arcs(topology)
    numeric_to_alpha2 = {row[2]: row[0] for row in fetch(CODES)}

    paths: dict[str, str] = {}
    names: dict[str, str] = {}
    skipped: list[str] = []

    for geom in topology["objects"]["countries"]["geometries"]:
        alpha2 = numeric_to_alpha2.get(str(geom.get("id", "")).zfill(3))
        name = (geom.get("properties") or {}).get("name", "")
        if not alpha2:
            # Natural Earth carries a few entities with no ISO numeric of their
            # own (Kosovo, N. Cyprus, Somaliland). Dropping them is honest: the
            # demographics buckets are alpha-2, so nothing could ever key to them.
            skipped.append(name or str(geom.get("id")))
            continue

        if geom["type"] == "Polygon":
            rings = [ring_points(r, arcs) for r in geom["arcs"]]
        elif geom["type"] == "MultiPolygon":
            rings = [ring_points(r, arcs) for poly in geom["arcs"] for r in poly]
        else:
            continue

        d = to_path(rings)
        if d:
            paths[alpha2] = d
            names[alpha2] = name

    body = ",\n".join(f"  {k}: '{paths[k]}'" for k in sorted(paths))
    label = ",\n".join(f"  {k}: {json.dumps(names[k])}" for k in sorted(names))

    OUT.write_text(f"""/** One SVG path per country, ISO 3166-1 alpha-2.
 *
 *  Generated by `scripts/build_country_paths.py` from Natural Earth 110m, in the
 *  same equirectangular frame as `land.ts`: x = (lon + 180) / 360 and
 *  y = (78 - lat) / 150, over a {W}x{H} viewBox. Do not hand-edit — and do not
 *  re-project one file without re-projecting the other, or the choropleth will
 *  sit beside its own coastline rather than on it.
 *
 *  Committed rather than fetched: an audience breakdown should not go blank
 *  because a CDN is having a bad day.
 *
 *  {len(paths)} countries. Coordinates are rounded to a tenth of a viewBox unit,
 *  which is sub-pixel at any size this renders at and roughly halves the file.
 */
export const COUNTRY_PATHS: Record<string, string> = {{
{body},
}}

/** Natural Earth's own name for each, for the hover label. */
export const COUNTRY_NAMES: Record<string, string> = {{
{label},
}}
""", encoding="utf-8")

    print(f"wrote {OUT.relative_to(Path(__file__).resolve().parents[1])}")
    print(f"  {len(paths)} countries, {OUT.stat().st_size // 1024} KB")
    if skipped:
        print(f"  no ISO alpha-2, skipped: {', '.join(sorted(skipped))}")


if __name__ == "__main__":
    main()
