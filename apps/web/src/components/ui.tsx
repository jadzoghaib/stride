/** Shared primitives — the whole product renders through these, so the
 *  register stays consistent: microcaps labels, hairline panels, wave accents. */

import type { ReactNode } from 'react'
import { avatarHue, fmtNum, initials } from '../lib/format'
import { DIMENSIONS, type ScoreSummary } from '../types'

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const [a, b] = avatarHue(name)
  return (
    <div
      className="flex items-center justify-center rounded-full text-mist-100 font-semibold shrink-0"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        backgroundImage: `linear-gradient(135deg, ${a}, ${b})`,
      }}
      aria-hidden
    >
      {initials(name)}
    </div>
  )
}

export function Section({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="mt-8 first:mt-0">
      <div className="flex items-baseline justify-between border-b border-line pb-2 mb-4">
        <h2 className="microcaps">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

export function Meter({ value, height = 5 }: { value: number | null; height?: number }) {
  return (
    <div className="rounded-full bg-ink-700 overflow-hidden" style={{ height }}>
      <div
        className="h-full rounded-full wave-line"
        style={{ width: `${Math.max(0, Math.min(100, value ?? 0))}%` }}
      />
    </div>
  )
}

export function DimensionGrid({
  score,
  onSelect,
  selected,
}: {
  score: ScoreSummary | { dimensions: Record<string, number | null> } | null
  onSelect?: (key: string) => void
  selected?: string | null
}) {
  if (!score) return <EmptyNote text="No analytics yet — connect a platform to compute marketability." />
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {DIMENSIONS.map((d) => {
        const v = score.dimensions[d.key]
        const clickable = Boolean(onSelect)
        return (
          <button
            key={d.key}
            disabled={!clickable}
            onClick={() => onSelect?.(d.key)}
            className={`panel p-4 text-left ${clickable ? 'panel-hover cursor-pointer' : 'cursor-default'} ${
              selected === d.key ? 'border-pulse-500' : ''
            }`}
          >
            <div className="microcaps">{d.label}</div>
            <div className={`tnum mt-1 text-2xl font-semibold ${v === null ? 'text-mist-400 text-base' : 'text-mist-100'}`}>
              {v === null || v === undefined ? 'n/a' : v.toFixed(0)}
            </div>
            <div className="mt-2">
              <Meter value={v ?? 0} />
            </div>
          </button>
        )
      })}
    </div>
  )
}

export function CoverageChip({ coverage }: { coverage: ScoreSummary['coverage'] | null | undefined }) {
  if (!coverage) return <span className="chip">no analytics</span>
  const full = coverage.connected === coverage.total
  return (
    <span className="chip" title={coverage.missing.length ? `Missing: ${coverage.missing.join(', ')}` : 'Full platform coverage'}>
      <span className={`mr-1.5 inline-block h-1.5 w-1.5 rounded-full ${full ? 'bg-ok' : 'bg-warn'}`} />
      {coverage.connected} of {coverage.total} platforms
    </span>
  )
}

const STATUS_STYLE: Record<string, string> = {
  offered: 'text-warn border-warn/40',
  accepted: 'text-ok border-ok/40',
  completed: 'text-ok border-ok/40',
  declined: 'text-danger border-danger/40',
  withdrawn: 'text-mist-400 border-line',
  connected: 'text-ok border-ok/40',
  disconnected: 'text-mist-400 border-line',
  error: 'text-danger border-danger/40',
  listed: 'text-ok border-ok/40',
  draft: 'text-warn border-warn/40',
  active: 'text-ok border-ok/40',
  closed: 'text-mist-400 border-line',
}

export function StatusChip({ status }: { status: string }) {
  return <span className={`chip bg-transparent ${STATUS_STYLE[status] ?? ''}`}>{status}</span>
}

export function EmptyNote({ text, action }: { text: string; action?: ReactNode }) {
  return (
    <div className="panel px-5 py-8 text-center text-mist-400">
      <p>{text}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

export function ShareBar({ data, max, highlight }: { data: Record<string, number>; max?: number; highlight?: Set<string> }) {
  const top = max ?? Math.max(...Object.values(data), 0.01)
  return (
    <div className="space-y-1.5">
      {Object.entries(data).map(([bucket, share]) => (
        <div key={bucket} className="grid grid-cols-[64px_1fr_48px] items-center gap-2 text-xs">
          <span className="text-mist-300 truncate">{bucket}</span>
          <div className="h-2.5 rounded-sm bg-ink-800 overflow-hidden">
            <div
              className={`h-full rounded-sm ${highlight?.has(bucket) ? 'wave-line' : 'bg-ink-600'}`}
              style={{ width: `${(100 * share) / top}%` }}
            />
          </div>
          <span className="tnum text-right text-mist-400">{(100 * share).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  )
}

export function Sparkline({ points, width = 120, height = 28 }: { points: number[]; width?: number; height?: number }) {
  if (points.length < 2) return <span className="text-xs text-mist-400">—</span>
  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  const path = points
    .map((v, i) => `${((i / (points.length - 1)) * (width - 2) + 1).toFixed(1)},${(height - 3 - ((v - min) / span) * (height - 6)).toFixed(1)}`)
    .join(' ')
  return (
    <svg width={width} height={height} aria-label="trend">
      <polyline points={path} fill="none" stroke="#585ceb" strokeWidth={2} strokeLinejoin="round" />
    </svg>
  )
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: string }) {
  return (
    <div className="panel px-5 py-4">
      <div className="microcaps">{label}</div>
      <div className="tnum mt-1 text-2xl font-semibold text-mist-100">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-mist-400">{sub}</div>}
    </div>
  )
}

export { fmtNum }
