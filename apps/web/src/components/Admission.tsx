/** Shared admission pieces: the verdict banner and the score decomposition.
 *
 *  Both the athlete and the club see the same thing about themselves, and the
 *  admin sees it about them — so it lives once, here. The rule the whole
 *  interface follows: **show the working**. A gate that returns a number and a
 *  verdict without the components behind them is a gate nobody can argue with,
 *  and this product has spent its whole design refusing to ask that of anyone.
 */

import type { ReactNode } from 'react'
import { Meter } from './ui'
import { fmtPct } from '../lib/format'
import { componentLabel, proofStatusLabel } from '../types'

/** The verdict, said in words, with what would move it. */
export function VerdictNote({
  decision,
  copy,
  notes,
}: {
  decision: string
  copy: string
  notes?: string[]
}) {
  // `verified` is the club-side spelling of `admitted`, and omitting it left a
  // green chip sitting above a neutral panel saying the same thing. `pending`
  // stays neutral on purpose — it is the absence of a decision, not a warning.
  const tone =
    decision === 'admitted' || decision === 'verified'
      ? 'border-ok/45 bg-ok/10'
      : decision === 'rejected'
        ? 'border-critical/45 bg-critical/10'
        : decision === 'review'
          ? 'border-warn/45 bg-warn/10'
          : 'border-line bg-raised'
  return (
    <div className={`rounded-card border px-4 py-3 ${tone}`}>
      {/* ink-2 rather than the semantic colour: this copy sits on a 10% tint of
          that same colour, where the tinted text measures under AA */}
      <p className="text-sm text-ink-2">{copy}</p>
      {notes?.map((n) => (
        <p key={n} className="meta mt-1.5 text-ink-2">
          {n}
        </p>
      ))}
    </div>
  )
}

/** Reasons and caveats, kept apart because they mean opposite things: one is
 *  what carried the score, the other is what held it back. */
export function ReasonLists({ reasons, caveats }: { reasons: string[]; caveats: string[] }) {
  if (!reasons.length && !caveats.length) return null
  return (
    <div className="grid gap-4 md:grid-cols-2">
      {reasons.length > 0 && (
        <div>
          <div className="cap mb-2">What counted for you</div>
          <ul className="space-y-1.5">
            {reasons.map((r) => (
              <li key={r} className="flex gap-2 text-sm text-ink-2">
                <span className="text-ok" aria-hidden>
                  +
                </span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}
      {caveats.length > 0 && (
        <div>
          <div className="cap mb-2">What held it back</div>
          <ul className="space-y-1.5">
            {caveats.map((c) => (
              <li key={c} className="flex gap-2 text-sm text-ink-2">
                <span className="text-warn" aria-hidden>
                  −
                </span>
                {c}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/** The arithmetic, opened up: each component, the weight it carried, and the
 *  evidence multiplier applied to the total. A component the applicant left
 *  blank is shown as blank and scored as zero — the interface says so rather
 *  than quietly folding it away. */
export function ScoreBreakdown({
  components,
  weights,
  missing,
  claim,
  multiplier,
  total,
  totalLabel,
  proofStatus,
}: {
  components: Record<string, number | null>
  weights: Record<string, number>
  missing: string[]
  claim: number
  multiplier: number
  total: number
  totalLabel: string
  proofStatus?: string
}) {
  return (
    <div>
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th className="table-head">Component</th>
            <th className="table-head text-right">Weight</th>
            <th className="table-head text-right">Score</th>
            <th className="table-head">Contribution</th>
          </tr>
        </thead>
        <tbody>
          {Object.keys(weights).map((key) => {
            const value = components[key]
            const blank = value === null || value === undefined
            return (
              <tr key={key}>
                <td className="table-cell text-ink">
                  {componentLabel(key)}
                  {blank && <span className="cap ml-2 text-warn">not supplied</span>}
                </td>
                <td className="table-cell tnum text-right text-ink-3">
                  {fmtPct(weights[key], 0)}
                </td>
                <td className="table-cell tnum text-right">
                  {blank ? '0' : fmtPct(value, 0)}
                </td>
                <td className="table-cell w-40">
                  <Meter value={(value ?? 0) * 100} height={5} muted={blank} />
                </td>
              </tr>
            )
          })}
          <tr>
            <td className="table-cell font-medium text-ink">Claim</td>
            <td className="table-cell" />
            <td className="table-cell tnum text-right font-medium text-ink">
              {claim.toFixed(1)}
            </td>
            <td className="table-cell" />
          </tr>
          <tr>
            <td className="table-cell text-ink">
              Evidence multiplier
              {proofStatus && (
                <span className="ml-2 text-xs text-ink-3">
                  proof {proofStatusLabel(proofStatus)}
                </span>
              )}
            </td>
            <td className="table-cell" />
            <td className="table-cell tnum text-right text-ink">×{multiplier.toFixed(2)}</td>
            <td className="table-cell" />
          </tr>
          <tr>
            <td className="table-cell font-display font-semibold uppercase tracking-board text-ink">
              {totalLabel}
            </td>
            <td className="table-cell" />
            <td className="table-cell tnum text-right font-display text-[19px] font-bold text-ink">
              {total.toFixed(1)}
            </td>
            <td className="table-cell" />
          </tr>
        </tbody>
      </table>
      {missing.length > 0 && (
        <p className="meta mt-2">
          Blank fields score zero rather than being left out. Weights are only ever
          redistributed over measurements we could not take — never over answers you
          chose not to give, because then leaving a box empty would raise your score.
        </p>
      )}
    </div>
  )
}

/** Where a score sits against the bar it has to clear. */
export function ThresholdRule({
  value,
  admit,
  review,
  admitLabel = 'admitted',
  reviewLabel = 'reviewed',
}: {
  value: number
  admit: number
  review: number
  admitLabel?: string
  reviewLabel?: string
}) {
  // Ticks sit at their actual position on the 0-100 scale, not at the ends of
  // the bar. Flushing them left and right reads as "55 is the far end", which
  // tells an applicant at 15 that they are closer than they are.
  const marks = [
    { at: review, label: reviewLabel },
    { at: admit, label: admitLabel },
  ]
  return (
    <div>
      <div className="relative">
        <Meter value={value} height={8} muted={value < admit} />
        {marks.map((m) => (
          <span
            key={m.label}
            aria-hidden
            className="absolute top-0 h-2 w-px bg-ink-2"
            style={{ left: `${m.at}%` }}
          />
        ))}
      </div>
      <div className="relative mt-1.5 h-4">
        {marks.map((m) => (
          <span
            key={m.label}
            className="meta absolute -translate-x-1/2 whitespace-nowrap"
            style={{ left: `${m.at}%` }}
          >
            {m.at} — {m.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export function FormRow({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="cap">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-ink-3">{hint}</span>}
    </label>
  )
}
