/** Everything, across every campaign.
 *
 *  The counterpart to the per-campaign Analytics tab. A sponsor asks two
 *  different questions and they used to share one page: "how is the spring line
 *  going" (a campaign question) and "what are we getting for our money" (an
 *  org question). The campaign question moved inside the campaign; this is what
 *  is left, and it is the only place where comparing campaigns is the point.
 *
 *  Every figure is the campaign endpoint's own arithmetic, summed. Nothing is
 *  recomputed here, so a row and its campaign can never disagree.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyNote, LoadError, PageHeader, PageLoading, Section } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney, fmtNum } from '../../lib/format'
import type { SponsorWorkspace } from '../../types'
import SponsorPipeline from './Pipeline'

interface Totals {
  athletes: number; athletes_live: number; committed_eur: number
  posts_attached: number; deals_measured: number
  reach: number | null; engagements: number | null
  cost_per_1k_reach: number | null; cost_per_engagement: number | null
}

interface Row {
  id: number
  name: string
  status: string
  totals: Totals
  on_target: number | null
}

export default function SponsorAnalytics() {
  const [rows, setRows] = useState<Row[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    api.get<SponsorWorkspace>('/api/sponsor/workspace')
      .then(async (ws) => {
        const loaded = await Promise.all(ws.campaigns.map(async (c) => {
          const a = await api.get<{ totals: Totals; audience_estimate: { on_target_share: number | null } }>(
            `/api/campaigns/${c.id}/analytics`)
          return { id: c.id, name: c.name, status: c.status,
                   totals: a.totals, on_target: a.audience_estimate.on_target_share }
        }))
        if (alive) setRows(loaded)
      })
      .catch((e) => { if (alive) setError(errorText(e)) })
    return () => { alive = false }
  }, [])

  if (!rows) return error ? <LoadError text={error} /> : <PageLoading />

  //: Summed from the per-campaign figures rather than recomputed, so a total
  //  and the rows under it can never tell different stories. Reach is null
  //  until something is measured — zero would say the campaigns reached nobody.
  const measured = rows.filter((r) => r.totals.reach !== null)
  const reach = measured.reduce((n, r) => n + (r.totals.reach ?? 0), 0)
  const engagements = measured.reduce((n, r) => n + (r.totals.engagements ?? 0), 0)
  const committed = rows.reduce((n, r) => n + r.totals.committed_eur, 0)
  //: Only the spend that bought measured reach, exactly as the campaign
  //  endpoint does it — spend on deals nobody has delivered yet is committed,
  //  not spent against a result.
  const measuredSpend = measured.reduce((n, r) => n + (
    r.totals.cost_per_1k_reach !== null && r.totals.reach
      ? r.totals.cost_per_1k_reach * (r.totals.reach / 1000) : 0), 0)

  return (
    <div>
      <PageHeader
        eyebrow="Sponsor"
        title="Analytics"
        lede="Delivered performance across every campaign. Each campaign's own tab breaks these figures down to the posts behind them."
        aside={<span className="meta">{rows.length} campaign{rows.length === 1 ? '' : 's'}</span>}
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Committed" value={fmtMoney(committed)} note="deals accepted, across all campaigns" />
        <Metric label="Delivered reach" value={measured.length ? fmtNum(reach) : '—'}
                note={`${measured.length} of ${rows.length} campaigns measured`} />
        <Metric label="Engagements" value={measured.length ? fmtNum(engagements) : '—'}
                note="reach × engagement rate, per post" />
        <Metric label="Blended cost / 1k" value={reach ? fmtMoney(measuredSpend / (reach / 1000)) : '—'}
                note="only the spend that bought measured reach" />
      </div>

      <Section title="By campaign" aside={<span className="meta">open one for the athletes behind it</span>}>
        {rows.length === 0 ? (
          <EmptyNote text="No campaigns yet." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[46rem] text-sm">
              <thead>
                <tr>
                  <th className="table-head">Campaign</th>
                  <th className="table-head text-right">Athletes</th>
                  <th className="table-head text-right">Committed</th>
                  <th className="table-head text-right">Reach</th>
                  <th className="table-head text-right">Cost / 1k</th>
                  <th className="table-head text-right">On target</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id}>
                    <td className="table-cell">
                      <Link to={`/sponsor/campaigns/${r.id}?tab=analytics`}
                            className="text-ink hover:text-accent">{r.name}</Link>
                      <div className="meta">{r.status}</div>
                    </td>
                    <td className="table-cell tnum text-right">
                      {r.totals.athletes_live} / {r.totals.athletes}
                    </td>
                    <td className="table-cell tnum text-right">{fmtMoney(r.totals.committed_eur)}</td>
                    <td className="table-cell tnum text-right">{fmtNum(r.totals.reach)}</td>
                    <td className="table-cell tnum text-right">
                      {r.totals.cost_per_1k_reach !== null ? fmtMoney(r.totals.cost_per_1k_reach) : '—'}
                    </td>
                    <td className="table-cell tnum text-right">
                      {r.on_target !== null ? `${(100 * r.on_target).toFixed(0)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="meta mt-2">
          A dash is a measurement that does not exist yet, not a zero. “On target” is estimated from
          each athlete's audience mix weighted by delivered reach.
        </p>
      </Section>

      {/* The org-wide pipeline, which is what this page used to be. It still
          belongs somewhere, and this is where a cross-campaign view is the
          question rather than an accident of where the deals happened to sit. */}
      <Section title="Everything in flight" aside={<span className="meta">every offer this org has sent</span>}>
        <SponsorPipeline embedded />
      </Section>
    </div>
  )
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="panel p-4">
      <div className="cap text-ink-3">{label}</div>
      <div className="tnum mt-1 font-display text-head font-bold leading-none text-ink">{value}</div>
      <div className="meta mt-1.5">{note}</div>
    </div>
  )
}
