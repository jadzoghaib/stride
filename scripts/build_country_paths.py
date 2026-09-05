"""Generate the country shapes and names the audience map draws.

The audience map used to be bubbles at country centroids over a single merged
land silhouette. A bubble encodes magnitude as area, which people read badly,
and it sits *on* a country rather than being one — so Germany and France, whose
centroids are 500km apart, overlapped into one blob at map scale.

A choropleth needs the countries as separate shapes, which the old `land.ts`
could not provide: it was one path with every coastline merged into it. That
file is gone now; this script writes the thing that replaced it — a lookup from
ISO 3166-1 alpha-2 to a path string.

Two files come out, and the split is load-bearing rather than tidiness:

  * `country-paths.ts` — the shapes, ~102 kB, drawn by exactly one component.
    `charts.tsx` pulls it in with a dynamic `import()` so the bundler emits it
    as its own chunk. Statically imported it sat in the main bundle and every
    visitor downloaded a world map to read their inbox.
  * `countries.ts` — the names, ~3 kB, read by several views, plain import.

Write them back into one file and the chunk silently rejoins the main bundle.

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

COMPONENTS = Path(__file__).resolve().parents[1] / "apps/web/src/components"
OUT_PATHS = COMPONENTS / "country-paths.ts"
OUT_NAMES = COMPONENTS / "countries.ts"

#: The projection the map is drawn in, and therefore the only one this may
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


def unwrap(ring: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Make a ring's longitudes continuous across the antimeridian.

    Source coordinates live in [-180, 180], so a country straddling 180 degrees
    has consecutive points that jump from +179 to -179. Projected naively that
    is a horizontal line all the way back across the map: Russia drew a band
    over the whole top of the frame, Fiji a hairline through the middle, and
    both looked like rendering corruption rather than geography.

    Adding a running multiple of 360 to each point removes the jump. The ring
    then extends past the edge of the frame instead, which `to_path` resolves by
    also drawing it shifted a whole frame width -- so the far side reappears
    where it belongs, and the SVG viewport clips the rest.
    """
    out = [ring[0]]
    offset = 0.0
    prev = ring[0][0]                       # the *unwrapped* previous longitude
    for lon, lat in ring[1:]:
        # Comparing against the original previous longitude rather than the
        # unwrapped one leaves the offset unable to settle once it is non-zero,
        # and the ring stays as wide as it started.
        if lon + offset - prev > 180:
            offset -= 360
        elif lon + offset - prev < -180:
            offset += 360
        prev = lon + offset
        out.append((prev, lat))
    return out


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
    projected = []
    for ring in rings:
        points = [project(lon, lat) for lon, lat in unwrap(ring)]
        projected.append(points)
        # A ring left hanging off one edge by the unwrap belongs on the other
        # too -- Chukotka is Russian whichever side of the frame it lands on.
        xs = [x for x, _ in points]
        if max(xs) > W:
            projected.append([(x - W, y) for x, y in points])
        if min(xs) < 0:
            projected.append([(x + W, y) for x, y in points])
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
        # The projection crops to 78N/-72S because nobody's audience lives in the
        # polar dead space. Antarctica is the remainder of that argument: it
        # spans every longitude, so it renders as a grey band across the foot of
        # the frame, and no demographics bucket can ever key to it.
        if alpha2 == "AQ":
            skipped.append("Antarctica (outside the projection's useful range)")
            continue
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

    OUT_PATHS.write_text(f"""/** One SVG path per country, ISO 3166-1 alpha-2.
 *
 *  Generated by `scripts/build_country_paths.py` from Natural Earth 110m, in an
 *  equirectangular frame: x = (lon + 180) / 360 and y = (78 - lat) / 150, over a
 *  {W}x{H} viewBox. Do not hand-edit.
 *
 *  Committed rather than fetched: an audience breakdown should not go blank
 *  because a CDN is having a bad day.
 *
 *  {len(paths)} countries. Coordinates are rounded to a tenth of a viewBox unit, which is
 *  sub-pixel at any size this renders at and roughly halves the file.
 *
 *  Kept apart from `countries.ts` because of its size. At ~102 kB this is the
 *  single largest thing the client ships, and exactly one component draws it,
 *  so `charts.tsx` pulls it in with a dynamic `import()` and the bundler gives
 *  it its own chunk. Import it statically and it lands back in the main bundle,
 *  where every visitor pays for it on the sign-in page.
 */
export const COUNTRY_PATHS: Record<string, string> = {{
{body},
}}
""", encoding="utf-8")

    OUT_NAMES.write_text(f"""/** Natural Earth's own name for each country, ISO 3166-1 alpha-2.
 *
 *  Generated by `scripts/build_country_paths.py` alongside `country-paths.ts`.
 *  Small (~3 kB) and read by several views, so unlike the path data this one is
 *  a plain static import.
 */
export const COUNTRY_NAMES: Record<string, string> = {{
{label},
}}
""", encoding="utf-8")

    root = Path(__file__).resolve().parents[1]
    for out in (OUT_PATHS, OUT_NAMES):
        print(f"wrote {out.relative_to(root)}  ({out.stat().st_size // 1024} KB)")
    print(f"  {len(paths)} countries")
    if skipped:
        print(f"  no ISO alpha-2, skipped: {', '.join(sorted(skipped))}")


if __name__ == "__main__":
    main()
