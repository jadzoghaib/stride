/** Audience visualizations — one system, three forms (dataviz method):
 *    age     -> vertical bar chart (magnitude across ordered buckets)
 *    gender  -> donut (parts of a small whole, 3 fixed-order identity colors,
 *               never color-alone: direct % labels + legend)
 *    country -> bubble map on an equirectangular graticule (true centroids,
 *               area ~ share) with a ranked list as the table view
 *  Values render in ink tokens, marks carry the color; native <title> tooltips.
 */

import type { ReactNode } from 'react'

const AGE_ORDER = ['13-17', '18-24', '25-34', '35-44', '45-54', '55+']

// validated categorical slots (dataviz reference palette): blue / aqua / yellow
const GENDER_SLOTS: [string, string][] = [
  ['female', '#2a78d6'],
  ['male', '#1baf7a'],
  ['other', '#eda100'],
]

const pct = (x: number) => `${(100 * x).toFixed(1)}%`

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="panel p-4">
      <div className="microcaps mb-3">{title}</div>
      {children}
    </div>
  )
}

// ── Age: bar chart ───────────────────────────────────────────────────────────

export function AgeBars({ data }: { data: Record<string, number> }) {
  const buckets = AGE_ORDER.filter((b) => b in data)
  const max = Math.max(...buckets.map((b) => data[b]), 0.01)
  const W = 320
  const H = 150
  const bw = W / buckets.length
  return (
    <ChartCard title="Age">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Audience by age">
        <defs>
          <linearGradient id="agegrad" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0" stopColor="#6366f1" />
            <stop offset="1" stopColor="#8b5cf6" />
          </linearGradient>
        </defs>
        {buckets.map((b, i) => {
          const h = (data[b] / max) * (H - 46)
          const x = i * bw + bw * 0.18
          const y = H - 26 - h
          return (
            <g key={b} className="transition-opacity hover:opacity-80">
              <title>{`${b}: ${pct(data[b])}`}</title>
              <rect x={x} y={y} width={bw * 0.64} height={Math.max(h, 2)} rx={4}
                    fill="url(#agegrad)" />
              <text x={i * bw + bw / 2} y={y - 6} textAnchor="middle"
                    fontSize="10" fill="#565367" style={{ fontVariantNumeric: 'tabular-nums' }}>
                {pct(data[b])}
              </text>
              <text x={i * bw + bw / 2} y={H - 10} textAnchor="middle"
                    fontSize="9.5" fill="#77748a">
                {b}
              </text>
            </g>
          )
        })}
      </svg>
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
  return (
    <ChartCard title="Gender">
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 124 124" className="w-28 shrink-0" role="img" aria-label="Audience by gender">
          {arcs.map((a) => (
            <path key={a.key} d={a.d} fill={a.color} className="transition-opacity hover:opacity-80">
              <title>{`${a.key}: ${pct(a.frac)}`}</title>
            </path>
          ))}
        </svg>
        <div className="space-y-1.5 text-xs">
          {arcs.map((a) => (
            <div key={a.key} className="flex items-center gap-2">
              <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: a.color }} />
              <span className="capitalize text-mist-300">{a.key}</span>
              <span className="tnum ml-auto pl-3 text-mist-100">{pct(a.frac)}</span>
            </div>
          ))}
        </div>
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

export function CountryMap({ data }: { data: Record<string, number> }) {
  const W = 560
  const H = 270
  const px = (lon: number) => ((lon + 180) / 360) * W
  const py = (lat: number) => ((78 - lat) / 150) * H // crop polar dead space
  const mapped = Object.entries(data)
    .filter(([code]) => code in CENTROIDS)
    .sort((a, b) => b[1] - a[1])
  const ranked = Object.entries(data).sort((a, b) => b[1] - a[1])
  const maxShare = Math.max(...mapped.map(([, s]) => s), 0.01)

  return (
    <ChartCard title="Countries">
      <div className="grid gap-4 sm:grid-cols-[1fr_130px]">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full rounded-xl bg-ink-850"
             role="img" aria-label="Audience by country">
          <defs>
            <radialGradient id="bubble" cx="0.35" cy="0.3" r="1">
              <stop offset="0" stopColor="#8b5cf6" />
              <stop offset="1" stopColor="#4a4dd8" />
            </radialGradient>
          </defs>
          {/* graticule */}
          {Array.from({ length: 11 }).map((_, i) => (
            <line key={`v${i}`} x1={(i + 1) * (W / 12)} y1={8} x2={(i + 1) * (W / 12)} y2={H - 8}
                  stroke="rgba(24,22,40,0.06)" strokeWidth={1} />
          ))}
          {Array.from({ length: 5 }).map((_, i) => (
            <line key={`h${i}`} x1={8} y1={(i + 1) * (H / 6)} x2={W - 8} y2={(i + 1) * (H / 6)}
                  stroke="rgba(24,22,40,0.06)" strokeWidth={1} />
          ))}
          {/* equator hint */}
          <line x1={8} y1={py(0)} x2={W - 8} y2={py(0)} stroke="rgba(24,22,40,0.12)"
                strokeWidth={1} strokeDasharray="3 5" />
          {mapped.map(([code, share]) => {
            const c = CENTROIDS[code]
            const radius = 7 + Math.sqrt(share / maxShare) * 22
            return (
              <g key={code} className="transition-opacity hover:opacity-85">
                <title>{`${c.name}: ${pct(share)}`}</title>
                <circle cx={px(c.lon)} cy={py(c.lat)} r={radius}
                        fill="url(#bubble)" fillOpacity={0.85}
                        stroke="#ffffff" strokeWidth={2} />
                <text x={px(c.lon)} y={py(c.lat) + 3.5} textAnchor="middle"
                      fontSize={radius > 14 ? 11 : 9} fontWeight={700} fill="#ffffff">
                  {code}
                </text>
              </g>
            )
          })}
        </svg>
        <div className="space-y-1 self-center text-xs">
          {ranked.slice(0, 6).map(([code, share]) => (
            <div key={code} className="flex items-center gap-2">
              <span className="w-10 text-mist-300">{code}</span>
              <span className="h-1.5 flex-1 rounded-full bg-ink-800">
                <span className="block h-full rounded-full wave-line"
                      style={{ width: `${(100 * share) / (ranked[0][1] || 1)}%` }} />
              </span>
              <span className="tnum text-mist-100">{pct(share)}</span>
            </div>
          ))}
        </div>
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
