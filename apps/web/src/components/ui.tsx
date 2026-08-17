/** Shared primitives — the whole product renders through these, so the register
 *  stays consistent: condensed board type, ranked lanes, signed deltas, one
 *  amber accent. Motion is a single settling sequence on mount; everything here
 *  checks prefers-reduced-motion before animating. */

import { ArrowUpRight } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { avatarHue, fmtNum, initials } from '../lib/format'
import { DIMENSIONS, type ScoreSummary } from '../types'

// ── motion helpers ───────────────────────────────────────────────────────────

export function useReducedMotion() {
  const [reduce, setReduce] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const on = () => setReduce(mq.matches)
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [])
  return reduce
}

/** Numerals roll up and settle, the way a scoreboard resolves. `format` lets a
 *  board headline that is not a 0-100 score (money, a count) roll up too. */
export function useCountUp(
  to: number | null | undefined,
  dp = 0,
  dur = 950,
  format?: (n: number) => string,
) {
  const reduce = useReducedMotion()
  const target = to ?? 0
  const [n, setN] = useState(() => (reduce ? target : 0))
  const frame = useRef(0)

  useEffect(() => {
    if (reduce) {
      setN(target)
      return
    }
    const t0 = performance.now()
    const step = (now: number) => {
      const p = Math.min(1, (now - t0) / dur)
      setN(target * (1 - Math.pow(1 - p, 3)))
      if (p < 1) frame.current = requestAnimationFrame(step)
    }
    frame.current = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame.current)
  }, [target, dur, reduce])

  if (to === null || to === undefined) return '—'
  return format ? format(n) : n.toFixed(dp)
}

/** Fades a block in on mount. `delay` staggers siblings into a sequence. */
export function Rise({ delay = 0, className = '', children }: { delay?: number; className?: string; children: ReactNode }) {
  return (
    <div className={`rise ${className}`} style={{ animationDelay: `${delay}ms` }}>
      {children}
    </div>
  )
}

// ── identity ─────────────────────────────────────────────────────────────────

export function Avatar({ name, size = 40 }: { name: string; size?: number }) {
  const [a, b] = avatarHue(name)
  return (
    <div
      className="flex shrink-0 items-center justify-center rounded-full font-display font-bold tracking-board text-[#F2F4F7]"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.38,
        backgroundImage: `linear-gradient(140deg, ${a}, ${b})`,
      }}
      aria-hidden
    >
      {initials(name)}
    </div>
  )
}

/** The page header for views that have no single headline figure.
 *
 *  Board.tsx covers the views that do. Between them these are the only two ways
 *  a view opens, so the board register reaches every surface: a view either
 *  reports a figure (Board) or it does not (PageHeader), and nothing falls back
 *  to an unstyled heading in the body face. */
export function PageHeader({
  eyebrow,
  title,
  lede,
  tags,
  aside,
}: {
  eyebrow?: ReactNode
  title: string
  lede?: ReactNode
  tags?: ReactNode
  aside?: ReactNode
}) {
  return (
    <header className="mb-8">
      {eyebrow && <div className="cap mb-1.5">{eyebrow}</div>}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className="text-[30px] leading-tight tracking-board">{title}</h1>
        {tags}
        {aside && <div className="ml-auto">{aside}</div>}
      </div>
      {lede && <p className="mt-2 max-w-2xl text-sm text-ink-3">{lede}</p>}
    </header>
  )
}

/** A modal built on the native <dialog>.
 *
 *  `showModal()` is what makes this a dialog rather than a floating div: the
 *  platform moves focus in, traps it, makes the rest of the page inert, closes
 *  on Escape, and restores focus to the trigger on close. Page scroll is the
 *  one thing it does not lock, so that is done here.
 *
 *  A backdrop click deliberately does NOT close it: these dialogs hold typed
 *  input, and a stray click outside should not discard an offer someone has
 *  written. Escape and the explicit Cancel control are the ways out. */
export function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  /** Called once the dialog has actually closed — unmount it here. */
  onClose: () => void
  /** Given the platform close request, so controls inside route through it. */
  children: (close: () => void) => ReactNode
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useRef(`modal-${Math.random().toString(36).slice(2, 9)}`).current
  // kept current so the `close` listener below can stay bound once
  const onCloseRef = useRef(onClose)
  useEffect(() => {
    onCloseRef.current = onClose
  })

  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (!el.open) el.showModal()
    // showModal() handles focus, the focus trap and inertness; page scroll is
    // the one thing it leaves alone. Cleanup clears the property rather than
    // restoring a captured value: StrictMode runs this effect twice, so the
    // second run would capture the lock set by the first and never release it.
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  /** Close through the element first, then unmount.
   *
   *  `close()` is what returns focus to the control that opened the dialog —
   *  unmounting an open dialog skips that and drops focus on <body>. The `close`
   *  event is deliberately not relied on to trigger the unmount: it does not
   *  bubble, React's synthetic `onClose` does not fire for <dialog>, and this
   *  browser does not emit it for a scripted `close()` either. Escape routes
   *  through the same function via onCancel. */
  const requestClose = () => {
    ref.current?.close()
    onCloseRef.current()
  }

  return (
    <dialog
      ref={ref}
      className="modal"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault() // take the same explicit path as every other close
        requestClose()
      }}
    >
      <div className="panel p-6">
        <h2 id={titleId} className="mb-4 text-[21px] leading-tight tracking-board">
          {title}
        </h2>
        {children(requestClose)}
      </div>
    </dialog>
  )
}

export function Section({ title, aside, id, children }: { title: string; aside?: ReactNode; id?: string; children: ReactNode }) {
  return (
    <section className="mt-10 scroll-mt-24 first:mt-0" id={id}>
      <div className="mb-4 flex items-baseline justify-between gap-4 border-b border-line-strong pb-2.5">
        <h2 className="cap">{title}</h2>
        {aside}
      </div>
      {children}
    </section>
  )
}

// ── meters ───────────────────────────────────────────────────────────────────

/** Bar wipes out from left on mount; `delay` staggers a stack of them. */
export function Meter({ value, height = 6, delay = 0, muted = false }: { value: number | null; height?: number; delay?: number; muted?: boolean }) {
  const reduce = useReducedMotion()
  const [run, setRun] = useState(reduce)
  const pct = Math.max(0, Math.min(100, value ?? 0))

  useEffect(() => {
    if (reduce) {
      setRun(true)
      return
    }
    const t = setTimeout(() => setRun(true), 340 + delay)
    return () => clearTimeout(t)
  }, [reduce, delay])

  return (
    <div className="bar" style={{ height }}>
      <i
        className={muted ? 'muted' : undefined}
        style={{
          width: `${pct}%`,
          transform: run ? 'scaleX(1)' : 'scaleX(0)',
          transition: reduce ? undefined : 'transform .85s cubic-bezier(.16,1,.3,1)',
        }}
      />
    </div>
  )
}

// ── ranked dimension lanes ───────────────────────────────────────────────────

/** Below this, a lane bar renders neutral instead of amber — the accent marks
 *  strength, so a weak dimension should not read as an emphasised one. */
const STRONG_ENOUGH = 65

/** Now that `warn` is its own hue rather than a second amber, confidence can
 *  read as a real gradient: earned / unremarkable / worth flagging. */
const CONFIDENCE_TONE: Record<string, string> = {
  high: 'text-ok',
  medium: 'text-ink-2',
  low: 'text-warn',
}

/** The five marketability dimensions as ranked lanes. The lane number is the
 *  athlete's actual rank on that dimension, so the numbering carries
 *  information instead of decorating rows. */
export function DimensionGrid({
  score,
  onSelect,
  selected,
  confidence,
}: {
  score: ScoreSummary | { dimensions: Record<string, number | null> } | null
  onSelect?: (key: string) => void
  selected?: string | null
  confidence?: Record<string, { confidence: string | null } | undefined>
}) {
  if (!score) return <EmptyNote text="No analytics yet — connect a platform to compute marketability." />

  const ranked = DIMENSIONS.map((d) => ({ ...d, value: score.dimensions[d.key] ?? null })).sort(
    (a, b) => (b.value ?? -1) - (a.value ?? -1),
  )
  const clickable = Boolean(onSelect)

  return (
    <div className="panel overflow-hidden">
      {ranked.map((d, i) => {
        const conf = confidence?.[d.key]?.confidence ?? null
        return (
          <button
            key={d.key}
            type="button"
            disabled={!clickable}
            aria-pressed={selected === d.key}
            onClick={() => onSelect?.(d.key)}
            className={`lane ${clickable ? 'cursor-pointer' : 'cursor-default'}`}
          >
            <span className="lane-no">{d.value === null ? '—' : i + 1}</span>
            <span className="lane-name">{d.label}</span>
            <span className={d.value === null ? 'font-display text-sm uppercase tracking-micro text-ink-3' : 'lane-val'}>
              {d.value === null ? 'n/a' : d.value.toFixed(0)}
            </span>
            <span className="lane-bar">
              <Meter value={d.value} delay={i * 85} muted={(d.value ?? 0) < STRONG_ENOUGH} />
            </span>
            <span className={`lane-conf cap ${conf ? CONFIDENCE_TONE[conf] ?? '' : ''}`}>
              {conf ?? (d.value === null ? 'no data' : '')}
            </span>
          </button>
        )
      })}
    </div>
  )
}

// ── state chips ──────────────────────────────────────────────────────────────

/** Partial coverage is *information*, not a warning — it is the normal state for
 *  most athletes, and colouring it amber put a caution mark on 19 of 22 rows of
 *  the directory while amber also meant emphasis. Full coverage earns the
 *  positive mark; anything less reads as a neutral fact. */
export function CoverageChip({ coverage }: { coverage: ScoreSummary['coverage'] | null | undefined }) {
  if (!coverage) return <span className="tag">no analytics</span>
  const full = coverage.connected === coverage.total
  return (
    <span
      className={`tag ${full ? 'border-ok/45 bg-ok/10 text-ok' : ''}`}
      title={coverage.missing.length ? `Missing: ${coverage.missing.join(', ')}` : 'Full platform coverage'}
    >
      {coverage.connected} of {coverage.total} platforms
    </span>
  )
}

const STATUS_STYLE: Record<string, string> = {
  offered: 'border-warn/45 bg-warn/10 text-warn',
  accepted: 'border-ok/45 bg-ok/10 text-ok',
  completed: 'border-ok/45 bg-ok/10 text-ok',
  declined: 'border-critical/45 bg-critical/10 text-critical',
  withdrawn: '',
  connected: 'border-ok/45 bg-ok/10 text-ok',
  disconnected: '',
  error: 'border-critical/45 bg-critical/10 text-critical',
  listed: 'border-ok/45 bg-ok/10 text-ok',
  draft: 'border-warn/45 bg-warn/10 text-warn',
  active: 'border-ok/45 bg-ok/10 text-ok',
  closed: '',
}

export function StatusChip({ status }: { status: string }) {
  return <span className={`tag ${STATUS_STYLE[status] ?? ''}`}>{status}</span>
}

// ── load / empty / error states ──────────────────────────────────────────────

export function PageLoading({ rows = 3 }: { rows?: number }) {
  return (
    <div className="animate-pulse space-y-5" aria-label="Loading" role="status">
      <div className="h-9 w-64 rounded bg-raised" />
      <div className="grid gap-3 md:grid-cols-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-24 rounded-card bg-raised" />
        ))}
      </div>
      <div className="h-72 rounded-card bg-raised/60" />
    </div>
  )
}

export function LoadError({ text }: { text: string }) {
  return (
    <div className="panel border-critical/45 px-5 py-7 text-center">
      <div className="cap text-critical">Couldn't load this page</div>
      <p className="mt-2 text-sm text-ink-2">{text}</p>
      <button className="btn mt-4" onClick={() => window.location.reload()}>
        Try again
      </button>
    </div>
  )
}

export function EmptyNote({ text, action }: { text: string; action?: ReactNode }) {
  return (
    <div className="panel px-5 py-9 text-center text-ink-3">
      <p>{text}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  )
}

// ── data marks ───────────────────────────────────────────────────────────────

export function ShareBar({ data, max, highlight }: { data: Record<string, number>; max?: number; highlight?: Set<string> }) {
  const top = max ?? Math.max(...Object.values(data), 0.01)
  return (
    <div className="space-y-1.5">
      {Object.entries(data).map(([bucket, share], i) => (
        <div key={bucket} className="grid grid-cols-[64px_1fr_52px] items-center gap-2.5 text-xs">
          <span className="truncate text-ink-2">{bucket}</span>
          <Meter value={(100 * share) / top} height={9} delay={i * 55} muted={!highlight?.has(bucket) && Boolean(highlight)} />
          <span className="tnum text-right text-ink-3">{(100 * share).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  )
}

/** Trend line with an area fade and an emphasised endpoint — the endpoint is
 *  the value that matters, so it gets the only filled mark. */
export function Sparkline({ points, width = 200, height = 56 }: { points: number[]; width?: number; height?: number }) {
  const gid = useRef(`spark-${Math.random().toString(36).slice(2, 9)}`).current
  if (points.length < 2) return <span className="text-xs text-ink-3">—</span>

  const min = Math.min(...points)
  const max = Math.max(...points)
  const span = max - min || 1
  const x = (i: number) => (i / (points.length - 1)) * (width - 6) + 3
  const y = (v: number) => height - 6 - ((v - min) / span) * (height - 14)
  const line = points.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
  const area = `M${line.split(' ').join(' L')} L${x(points.length - 1).toFixed(1)},${height} L${x(0).toFixed(1)},${height} Z`

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="trend">
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" style={{ stopColor: 'rgb(var(--c-accent))', stopOpacity: 0.26 }} />
          <stop offset="100%" style={{ stopColor: 'rgb(var(--c-accent))', stopOpacity: 0 }} />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gid})`} />
      <polyline points={line} className="stroke-accent" fill="none" strokeWidth={2.25} strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={x(points.length - 1)} cy={y(points[points.length - 1])} r={3.5} className="fill-accent" />
    </svg>
  )
}

/** A signed change. Direction is carried by the arrow and the word, not colour
 *  alone, so it survives a colour-blind read and a greyscale print. */
export function Delta({ value, suffix = '%', dp = 1 }: { value: number | null | undefined; suffix?: string; dp?: number }) {
  if (value === null || value === undefined) return <span className="meta">—</span>
  const up = value >= 0
  return (
    <span className={`tnum inline-flex items-center gap-1 font-display font-bold ${up ? 'text-ok' : 'text-critical'}`}>
      <span aria-hidden>{up ? '▲' : '▼'}</span>
      <span>
        {up ? '+' : ''}
        {value.toFixed(dp)}
        {suffix}
      </span>
      <span className="sr-only">{up ? 'increase' : 'decrease'}</span>
    </span>
  )
}

// ── figures ──────────────────────────────────────────────────────────────────

export function Stat({ label, value, sub, to }: { label: string; value: ReactNode; sub?: string; to?: string }) {
  const body = (
    <>
      <div className="flex items-start justify-between">
        <div className="cap">{label}</div>
        {to && (
          <ArrowUpRight
            size={14}
            className="text-ink-3 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-accent"
          />
        )}
      </div>
      <div className="tnum mt-1.5 font-display text-[32px] font-bold leading-none text-ink">{value}</div>
      {sub && <div className="mt-1.5 text-xs text-ink-3">{sub}</div>}
    </>
  )
  if (to) {
    return (
      <Link to={to} className="panel panel-hover group block px-5 py-4" title={`Go to ${label.toLowerCase()}`}>
        {body}
      </Link>
    )
  }
  return <div className="panel px-5 py-4">{body}</div>
}

/** Compact label/value pair for the board footer strip. Given `to`, it becomes
 *  a deep link — the board is a readout, but the readouts are the fastest route
 *  into the section behind them. */
export function KV({ label, value, to }: { label: string; value: ReactNode; to?: string }) {
  const body = (
    <>
      <span className="cap">{label}</span>
      <b className="tnum font-display text-[19px] font-bold text-ink">{value}</b>
      {to && (
        <ArrowUpRight
          size={13}
          className="text-ink-3 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-accent"
        />
      )}
    </>
  )
  if (to) {
    return (
      <Link to={to} className="group flex items-baseline gap-2.5" title={`Go to ${label.toLowerCase()}`}>
        {body}
      </Link>
    )
  }
  return <div className="flex items-baseline gap-2.5">{body}</div>
}

export { fmtNum }
