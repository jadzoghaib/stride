/** The board header — a full-bleed results board that opens a view.
 *
 *  It carries identity, the single headline figure at display scale, its signed
 *  change, a trend, and a strip of secondary figures. The point of the register
 *  is the scale gap: a ~110px numeral against 11px tracked caps. Rendered as a
 *  direct child of <main class="stride-main"> with `.bleed` so it spans the
 *  full width while the rest of the view stays in the column.
 */

import type { CSSProperties, ReactNode } from 'react'
import { Delta, KV, Rise, Sparkline, useCountUp } from './ui'

export function Board({
  eyebrow,
  title,
  tags,
  score,
  scoreFormat,
  scoreLabel = 'Marketability',
  rulePct,
  delta,
  deltaNote = '30-day change',
  trend,
  trendLabel,
  trendEmpty,
  figures,
  footNote,
  children,
}: {
  eyebrow?: ReactNode
  title: string
  tags?: ReactNode
  score?: number | null
  /** For a headline that is not a 0-100 score — money, a count. When set, the
   *  closing rule needs its own source, because the figure is no longer a
   *  percentage of anything. */
  scoreFormat?: (n: number) => string
  scoreLabel?: string
  /** Overrides what the closing rule fills to. The rule reports something true
   *  or it is decoration, so a board whose headline is not 0-100 must say what
   *  the rule measures instead. */
  rulePct?: number | null
  delta?: number | null
  deltaNote?: string
  trend?: number[]
  trendLabel?: string
  /** Shown where the trend would go when there is not enough history for one —
   *  an explanation reads better than an empty half-board. */
  trendEmpty?: ReactNode
  figures?: { label: string; value: ReactNode; to?: string }[]
  footNote?: ReactNode
  children?: ReactNode
}) {
  const shown = useCountUp(score, 0, 950, scoreFormat)
  // the closing rule doubles as the headline figure's meter
  const fill = typeof rulePct === 'number' ? rulePct : scoreFormat ? null : score
  const ruleStyle = {
    '--board-rule': typeof fill === 'number' ? `${Math.max(0, Math.min(100, fill))}%` : '100%',
  } as CSSProperties

  return (
    <header className="board bleed" style={ruleStyle}>
      <div className="relative mx-auto w-full max-w-page px-7 pb-8 pt-10">
        <Rise delay={40}>
          <div className="flex flex-wrap items-center gap-3">
            {eyebrow && <span className="cap">{eyebrow}</span>}
            <h1 className="text-display leading-tight tracking-board">{title}</h1>
            {tags}
          </div>
        </Rise>

        {(score !== undefined || trend) && (
          <div className="mt-7 flex flex-wrap items-end gap-x-10 gap-y-6">
            <Rise delay={110}>
              <div className="flex items-start gap-4">
                <div className="score">{score === null || score === undefined ? '—' : shown}</div>
                <div className="pt-2">
                  <div className="cap">{scoreLabel}</div>
                  {delta !== undefined && delta !== null && (
                    <div className="mt-0.5 text-lead">
                      <Delta value={delta} />
                    </div>
                  )}
                  <div className="meta mt-0.5">{deltaNote}</div>
                </div>
              </div>
            </Rise>

            {trend && trend.length > 1 ? (
              <Rise delay={200} className="ml-auto">
                <Sparkline points={trend} width={230} height={62} />
                {/* the trend series is named, because it is not always the same
                    metric as the headline figure */}
                {trendLabel && <div className="meta mt-1 text-right">{trendLabel}</div>}
              </Rise>
            ) : (
              trendEmpty && (
                <Rise delay={200} className="ml-auto max-w-56">
                  <div className="meta text-right">{trendEmpty}</div>
                </Rise>
              )
            )}
          </div>
        )}

        {children}

        {(figures?.length || footNote) && (
          <Rise delay={280}>
            <div className="mt-7 flex flex-wrap items-center gap-x-7 gap-y-3 border-t border-line pt-4">
              {figures?.map((f) => (
                <KV key={f.label} label={f.label} value={f.value} to={f.to} />
              ))}
              {footNote && <span className="meta ml-auto">{footNote}</span>}
            </div>
          </Rise>
        )}
      </div>
    </header>
  )
}
