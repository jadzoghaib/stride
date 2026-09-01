/** Audience visualizations — one system, three forms (dataviz method):
 *    age     -> vertical bar chart (magnitude across ordered buckets)
 *    gender  -> donut (parts of a small whole, 3 fixed-order identity colors,
 *               never color-alone: direct % labels + legend)
 *    country -> bubble map on an equirectangular graticule (true centroids,
 *               area ~ share) with a ranked list as the table view
 *
 *  Every mark draws from the theme tokens rather than literal hex, so the
 *  charts follow the page into dark or light. The one exception is the gender
 *  palette: those three hues are identity slots that must stay stable across
 *  themes, and they are legible on both grounds.
 */

import { useRef, useState, type ReactNode } from 'react'
import { COUNTRY_NAMES, COUNTRY_PATHS } from './countries'

const AGE_ORDER = ['13-17', '18-24', '25-34', '35-44', '45-54', '55+']

// validated categorical slots (dataviz reference palette): blue / aqua / yellow
const GENDER_SLOTS: [string, string][] = [
  ['female', '#3b86e0'],
  ['male', '#1fbd85'],
  ['other', '#f0a00c'],
]

const pct = (x: number) => `${(100 * x).toFixed(1)}%`

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="panel p-4">
      <div className="cap mb-3">{title}</div>
      {children}
    </div>
  )
}

/** A cursor-following tooltip, and the hovered key for cross-highlighting.
 *
 *  Every chart here shipped with an SVG `<title>`, which is a tooltip in the
 *  same sense that a fire escape is a lift: it works, roughly a second later,
 *  in the operating system's font, with no indication of which mark it belongs
 *  to. The `key` is returned alongside so a chart can dim what is not hovered
 *  and light up the matching row in its legend. */
function useHover() {
  const box = useRef<HTMLDivElement>(null)
  const [tip, setTip] = useState<{ text: string; key: string; x: number; y: number } | null>(null)

  const at = (e: { clientX: number; clientY: number }) => {
    const r = box.current?.getBoundingClientRect()
    return r ? { x: e.clientX - r.left, y: e.clientY - r.top } : { x: 0, y: 0 }
  }
  const enter = (key: string, text: string) => (e: React.MouseEvent) =>
    setTip({ key, text, ...at(e) })
  const move = (e: React.MouseEvent) => setTip((t) => (t ? { ...t, ...at(e) } : t))
  const leave = () => setTip(null)
  /** Spread on each mark. Four jobs:
   *
   *  - enter/leave per mark, because the wrapper's own leave fires only at the
   *    edge of the chart, so the tip and the dimming used to survive the pointer
   *    moving into empty space between marks;
   *  - focus/blur, so the same tip is reachable with a keyboard;
   *  - `aria-label` rather than an SVG `<title>`. `<title>` is what a screen
   *    reader reads *and* what the browser renders as its own delayed tooltip,
   *    so keeping it beside this one showed two tooltips for the same mark.
   *    `aria-label` gives the description without the second tooltip. */
  const on = (key: string, text: string) => ({
    onMouseEnter: enter(key, text),
    onMouseLeave: leave,
    onFocus: (e: React.FocusEvent) => {
      const r = box.current?.getBoundingClientRect()
      const m = (e.target as SVGGraphicsElement).getBoundingClientRect()
      setTip({ key, text, x: m.left - (r?.left ?? 0) + m.width / 2, y: m.top - (r?.top ?? 0) })
    },
    onBlur: leave,
    tabIndex: 0,
    role: 'img',
    'aria-label': text,
  })

  const Tip = () =>
    tip ? (
      <div
        className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[calc(100%+12px)]
                   whitespace-nowrap rounded border border-line-strong bg-panel px-2.5 py-1.5
                   font-mono text-[11px] text-ink shadow-lift"
        style={{ left: tip.x, top: tip.y }}
      >
        {tip.text}
      </div>
    ) : null

  return { box, key: tip?.key ?? null, enter, on, move, leave, Tip }
}

/** Dim what is not being hovered. Nothing dims until something is hovered, so
 *  the chart's resting state is unchanged. */
const focus = (hovered: string | null, key: string) =>
  hovered && hovered !== key ? 'opacity-35' : 'opacity-100'


// ── Age: bar chart ───────────────────────────────────────────────────────────

export function AgeBars({ data }: { data: Record<string, number> }) {
  const buckets = AGE_ORDER.filter((b) => b in data)
  const max = Math.max(...buckets.map((b) => data[b]), 0.01)
  const W = 320
  const H = 150
  const bw = W / buckets.length
  // `hov`, not `h`: the bar height inside the map below is already called `h`
  const hov = useHover()
  return (
    <ChartCard title="Age">
      <div ref={hov.box} className="relative" onMouseMove={hov.move} onMouseLeave={hov.leave}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Audience by age">
        {buckets.map((b, i) => {
          const h = (data[b] / max) * (H - 46)
          const x = i * bw + bw * 0.18
          const y = H - 26 - h
          const peak = data[b] === max
          return (
            <g
              key={b}
              className={`cursor-default transition-opacity ${focus(hov.key, b)}`}
              {...hov.on(b, `${b} · ${pct(data[b])} of audience`)}
            >
              {/* the modal bucket carries the accent; the rest stay neutral so
                  the shape of the distribution reads before the colour does */}
              <rect
                x={x}
                y={y}
                width={bw * 0.64}
                height={Math.max(h, 2)}
                rx={2}
                className={peak ? 'fill-accent' : 'fill-track'}
              />
              <text
                x={i * bw + bw / 2}
                y={y - 6}
                textAnchor="middle"
                fontSize="10"
                className="fill-ink-2"
                style={{ fontVariantNumeric: 'tabular-nums' }}
              >
                {pct(data[b])}
              </text>
              <text x={i * bw + bw / 2} y={H - 10} textAnchor="middle" fontSize="9.5" className="fill-ink-3">
                {b}
              </text>
            </g>
          )
        })}
      </svg>
      <hov.Tip />
      </div>
    </ChartCard>
  )
}

// ── Gender: donut ────────────────────────────────────────────────────────────

export function GenderDonut({ data }: { data: Record<string, number> }) {
  const slices = GENDER_SLOTS.filter(([k]) => k in data)
  const total = slices.reduce((s, [k]) => s + data[k], 0) || 1
  const R = 52
  const r = 32
  const C = 62
  let angle = -Math.PI / 2
  const arcs = slices.map(([key, color]) => {
    const frac = data[key] / total
    const a0 = angle
    const a1 = (angle += frac * Math.PI * 2)
    // 2px surface gap between segments (spacer rule): shrink each arc slightly
    const gap = 0.028
    const s = a0 + gap
    const e = Math.max(a1 - gap, s + 0.01)
    const large = e - s > Math.PI ? 1 : 0
    const p = (a: number, rad: number) => `${C + rad * Math.cos(a)},${C + rad * Math.sin(a)}`
    const d = `M ${p(s, R)} A ${R} ${R} 0 ${large} 1 ${p(e, R)} L ${p(e, r)} A ${r} ${r} 0 ${large} 0 ${p(s, r)} Z`
    return { key, color, frac, d }
  })
  const h = useHover()
  return (
    <ChartCard title="Gender">
      <div ref={h.box} className="relative" onMouseMove={h.move} onMouseLeave={h.leave}>
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 124 124" className="w-28 shrink-0" role="img" aria-label="Audience by gender">
          {arcs.map((a) => (
            <path
              key={a.key}
              d={a.d}
              fill={a.color}
              className={`cursor-default transition-opacity ${focus(h.key, a.key)}`}
              {...h.on(a.key, `${a.key} · ${pct(a.frac)} of audience`)}
            />
          ))}
        </svg>
        <div className="space-y-1.5 text-xs">
          {arcs.map((a) => (
            <div
              key={a.key}
              className={`flex items-center gap-2 rounded px-1 transition-colors ${
                h.key === a.key ? 'bg-raised' : ''
              }`}
              {...h.on(a.key, `${a.key} · ${pct(a.frac)} of audience`)}
            >
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: a.color }} />
              <span className="capitalize text-ink-2">{a.key}</span>
              <span className="tnum ml-auto pl-3 font-display font-semibold text-ink">{pct(a.frac)}</span>
            </div>
          ))}
        </div>
      </div>
      <h.Tip />
      </div>
    </ChartCard>
  )
}

// ── Country: bubble map ──────────────────────────────────────────────────────

const CENTROIDS: Record<string, { lat: number; lon: number; name: string }> = {
  US: { lat: 39.8, lon: -98.5, name: 'United States' },
  CA: { lat: 56.1, lon: -106.3, name: 'Canada' },
  MX: { lat: 23.6, lon: -102.5, name: 'Mexico' },
  BR: { lat: -14.2, lon: -51.9, name: 'Brazil' },
  GB: { lat: 54.0, lon: -2.0, name: 'United Kingdom' },
  FR: { lat: 46.6, lon: 2.2, name: 'France' },
  DE: { lat: 51.2, lon: 10.4, name: 'Germany' },
  ES: { lat: 40.3, lon: -3.7, name: 'Spain' },
  IN: { lat: 21.0, lon: 78.0, name: 'India' },
  AU: { lat: -25.3, lon: 133.8, name: 'Australia' },
}

/** Five steps, palest to deepest.
 *
 *  Opacities of the accent rather than five fixed hex values, because the map
 *  sits on `bg-ground-deep` and that ground is a different colour in each
 *  theme. A pale amber that reads correctly on the dark ground is very nearly
 *  invisible on the light one; the same amber at 18% composites against
 *  whichever ground is actually behind it and stays a fifth of the way up the
 *  ramp in both. */
const RAMP = [0.16, 0.34, 0.52, 0.72, 0.94]

/** Which step a share falls in — equal-width bins from zero to the largest
 *  share present, so the ramp spends its whole range on the data that is
 *  actually there rather than on the 0-100% a share could theoretically be. */
function step(share: number, max: number): number {
  if (max <= 0) return 0
  const i = Math.ceil((share / max) * RAMP.length) - 1
  return Math.min(RAMP.length - 1, Math.max(0, i))
}

export function CountryMap({ data }: { data: Record<string, number> }) {
  const W = 560
  const H = 270
  const py = (lat: number) => ((78 - lat) / 150) * H // crop polar dead space
  const ranked = Object.entries(data).sort((a, b) => b[1] - a[1])
  const h = useHover()

  /* A choropleth, not bubbles.
   *
   * The bubbles encoded share as circle *area*, which people compare badly, and
   * placed it at a country's centroid — so the mark sat on the country instead
   * of being it, and the European centroids are close enough at this width that
   * Germany, France and Great Britain overlapped into a single blob with the
   * labels fighting for the gaps. Filling the country says the same thing with
   * no placement problem and no label-avoidance code at all: the shape is the
   * label. */
  const shares = Object.entries(data).filter(([code]) => code in COUNTRY_PATHS)
  const maxShare = Math.max(...shares.map(([, v]) => v), 0.0001)
  const name = (code: string) => COUNTRY_NAMES[code] ?? CENTROIDS[code]?.name ?? code

  return (
    <ChartCard title="Countries">
      <div ref={h.box} className="relative" onMouseMove={h.move} onMouseLeave={h.leave}>
      <div className="grid gap-4 sm:grid-cols-[1fr_140px]">
        <div>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded bg-ground-deep"
               role="img" aria-label="Audience by country">
            {/* Every country, in the neutral land fill. This is the base map and
                also the "no data" state: a country nobody in this audience lives
                in is drawn, and drawn plainly, which is a different statement
                from not drawing it. */}
            <g className="fill-raised stroke-line" strokeWidth={0.35}>
              {Object.entries(COUNTRY_PATHS).map(([code, d]) => (
                <path key={code} d={d} />
              ))}
            </g>

            {/* equator, as the one line worth keeping from the graticule */}
            <line x1={8} y1={py(0)} x2={W - 8} y2={py(0)} className="stroke-line-strong"
                  strokeWidth={0.8} strokeDasharray="3 5" />

            {/* the data on top, so a filled country keeps its own outline */}
            {shares.map(([code, share]) => (
              <path
                key={code}
                d={COUNTRY_PATHS[code]}
                className={`cursor-default fill-accent transition-opacity ${focus(h.key, code)}`}
                fillOpacity={RAMP[step(share, maxShare)]}
                stroke={h.key === code ? 'currentColor' : 'none'}
                strokeWidth={h.key === code ? 1.2 : 0}
                {...h.on(code, `${name(code)} · ${pct(share)} of audience`)}
              />
            ))}
          </svg>

          {/* The legend. Without it the ramp is decoration — a reader can see
              that one country is darker than another and cannot say by how
              much. The end labels are the real bin edges, so the scale is
              readable rather than merely present. */}
          <div className="mt-2 flex items-center gap-2">
            <span className="meta">less</span>
            <div className="flex flex-1 gap-0.5">
              {RAMP.map((o, i) => (
                <div key={o} className="h-2 flex-1 rounded-[1px] bg-accent"
                     style={{ opacity: o }}
                     title={`${pct((i / RAMP.length) * maxShare)} – ${pct(((i + 1) / RAMP.length) * maxShare)}`} />
              ))}
            </div>
            <span className="meta">more</span>
            <span className="meta tnum ml-1">up to {pct(maxShare)}</span>
          </div>
        </div>

        <div className="space-y-1.5 self-center text-xs">
          {/* Cross-highlighted with the map: hovering either lights the other,
              which is the point of showing a chart and a table of the same
              numbers side by side. `OTHER` has no shape, so it dims nothing. */}
          {ranked.slice(0, 6).map(([code, share]) => (
            <div
              key={code}
              className={`flex items-center gap-2 rounded px-1 transition-colors ${
                h.key === code ? 'bg-raised' : ''
              }`}
              {...h.on(
                code in COUNTRY_PATHS ? code : '',
                `${name(code)} · ${pct(share)} of audience`,
              )}
            >
              <span className="w-8 font-display font-semibold uppercase tracking-board text-ink-2">{code}</span>
              <span className="bar h-1.5 flex-1">
                <i style={{ width: `${(100 * share) / (ranked[0][1] || 1)}%` }} />
              </span>
              <span className="tnum font-display font-semibold text-ink">{pct(share)}</span>
            </div>
          ))}
        </div>
      </div>
      <h.Tip />
      </div>
    </ChartCard>
  )
}

/** The composed audience panel: map full-width, age + gender beside each other. */
export function AudiencePanel({ audience }: { audience: Record<string, Record<string, number>> }) {
  if (!audience || !Object.keys(audience).length) return null
  return (
    <div className="space-y-3">
      {audience.country && <CountryMap data={audience.country} />}
      <div className="grid gap-3 md:grid-cols-2">
        {audience.age && <AgeBars data={audience.age} />}
        {audience.gender && <GenderDonut data={audience.gender} />}
      </div>
    </div>
  )
}
