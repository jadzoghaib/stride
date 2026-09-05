/** What the campaign actually did.
 *
 *  The pipeline answers "how is each deal going". This answers the question a
 *  sponsor asks their own management: what did the whole thing reach, what did
 *  it cost per unit of that, and which athletes carried it.
 *
 *  Two things on this page are deliberately not what they could be mistaken for.
 *
 *  Every figure decomposes to *posts an athlete attached to a deal* — not to
 *  their account. That join is the permission boundary, and it is why a sponsor
 *  can be shown real numbers at all.
 *
 *  The country split is an estimate and is labelled as one wherever it appears.
 *  No platform reports per-impression geography at post level; this is each
 *  athlete's own audience mix weighted by the reach they delivered. Presenting
 *  it as measured would be the easiest lie in the product to tell.
 */
import { ArrowLeft } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { CountryMap } from '../../components/charts'
import { EmptyNote, LoadError, PageHeader, PageLoading, Section, SimulatedChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney, fmtNum, fmtPct } from '../../lib/format'
import { dealTypeLabel } from '../../types'

interface AthleteRow {
  deal_id: number
  athlete_name: string
  athlete_slug: string
  sport: string
  status: string
  deal_type: string
  amount_eur: number
  posts: number
  reach: number | null
  engagements: number | null
  projected_reach: number | null
  variance_pct: number | null
  cost_per_1k_reach: number | null
}

interface Analytics {
  campaign: {
    id: number; name: string; status: string
    objective: string | null; category: string | null
    target_countries: string[]
  }
  totals: {
    athletes: number; athletes_live: number; committed_eur: number
    posts_attached: number; deals_measured: number
    reach: number | null; engagements: number | null
    cost_per_1k_reach: number | null; cost_per_engagement: number | null
  }
  athletes: AthleteRow[]
  audience_estimate: {
    by_country: Record<string, number>
    on_target_share: number | null
    basis: string
  }
}

export default function CampaignAnalytics({ embedded = false }: { embedded?: boolean } = {}) {
  const { id } = useParams()
  const [data, setData] = useState<Analytics | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Analytics>(`/api/campaigns/${id}/analytics`).then(setData).catch((e) => setError(errorText(e)))
  }, [id])

  if (!data) return error ? <LoadError text={error} /> : <PageLoading />

  const { campaign, totals, athletes, audience_estimate: est } = data
  const waiting = athletes.filter((a) => a.posts === 0 && (a.status === 'accepted' || a.status === 'completed'))

  return (
    <div>
      {!embedded && (
        <Link to="/sponsor" className="meta mb-3 inline-flex items-center gap-1.5 hover:text-accent">
          <ArrowLeft size={13} /> Campaigns
        </Link>
      )}

      {!embedded && (
      <PageHeader
          eyebrow="Campaign"
          title={campaign.name}
          lede={campaign.objective || 'Delivered performance across every athlete on this campaign.'}
          aside={<span className="meta">
            {totals.athletes_live} of {totals.athletes} live · {fmtMoney(totals.committed_eur)} committed
          </span>}
        />
      )}


      {/* ── the headline ───────────────────────────────────────────────── */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Delivered reach" value={fmtNum(totals.reach)}
                note={`${totals.posts_attached} post${totals.posts_attached === 1 ? '' : 's'} attached`} />
        <Metric label="Engagements" value={fmtNum(totals.engagements)}
                note="reach × engagement rate, per post" />
        <Metric label="Cost / 1k reach" value={totals.cost_per_1k_reach != null ? fmtMoney(totals.cost_per_1k_reach) : '—'}
                note="only the spend that bought measured reach" />
        <Metric label="Cost / engagement" value={totals.cost_per_engagement != null ? fmtMoney(totals.cost_per_engagement) : '—'}
                note="same denominator" />
      </div>

      {waiting.length > 0 && (
        // Said plainly rather than folded into the numbers. A campaign that is
        // half-delivered is not a campaign that under-performed, and the
        // difference matters to whoever reads the cost figures above.
        <p className="meta mt-3">
          {waiting.length} live deal{waiting.length === 1 ? ' has' : 's have'} nothing attached yet
          ({waiting.map((a) => a.athlete_name).join(', ')}). Their fee is committed and is excluded
          from the cost figures until there is something to measure.
        </p>
      )}

      {/* ── who carried it ─────────────────────────────────────────────── */}
      <Section title={`Athletes (${athletes.length})`}
               aside={<span className="flex items-center gap-2"><SimulatedChip what="analytics" /><span className="meta">every figure is the posts they attached</span></span>}>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[52rem] text-sm">
            <thead>
              <tr>
                <th className="table-head">Athlete</th>
                <th className="table-head">Status</th>
                <th className="table-head text-right">Fee</th>
                <th className="table-head text-right">Posts</th>
                <th className="table-head text-right">Reach</th>
                <th className="table-head text-right">Engagements</th>
                <th className="table-head text-right">vs projection</th>
                <th className="table-head text-right">Cost / 1k</th>
              </tr>
            </thead>
            <tbody>
              {athletes.map((a) => (
                <tr key={a.deal_id}>
                  <td className="table-cell">
                    <Link to={`/sponsor/athletes/${a.athlete_slug}`} className="text-ink hover:text-accent">
                      {a.athlete_name}
                    </Link>
                    <div className="meta">{a.sport} · {dealTypeLabel(a.deal_type)}</div>
                  </td>
                  <td className="table-cell"><span className="cap text-ink-3">{a.status}</span></td>
                  <td className="table-cell tnum text-right">{fmtMoney(a.amount_eur)}</td>
                  <td className="table-cell tnum text-right">{a.posts || '—'}</td>
                  <td className="table-cell tnum text-right">{fmtNum(a.reach)}</td>
                  <td className="table-cell tnum text-right">{fmtNum(a.engagements)}</td>
                  <td className="table-cell tnum text-right">
                    {a.variance_pct == null ? '—' : (
                      <span className={a.variance_pct >= 0 ? 'text-ok' : 'text-warn'}>
                        {a.variance_pct > 0 ? '+' : ''}{a.variance_pct.toFixed(1)}%
                      </span>
                    )}
                  </td>
                  <td className="table-cell tnum text-right">
                    {a.cost_per_1k_reach != null ? fmtMoney(a.cost_per_1k_reach) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="meta mt-2">
          A dash is a measurement that does not exist yet, not a zero. “vs projection” compares one
          delivered post against the one-post reach projected when the offer was priced.
        </p>
      </Section>

      {/* ── where it landed ────────────────────────────────────────────── */}
      <Section title="Where it landed"
               aside={<span className="meta">estimated, not measured</span>}>
        {Object.keys(est.by_country).length === 0 ? (
          <EmptyNote text="Nothing delivered yet, so there is nothing to place." />
        ) : (
          <>
            {campaign.target_countries.length > 0 && (
              <div className="panel mb-3 flex flex-wrap items-center gap-3 p-4">
                <div>
                  <div className="cap text-ink-3">On target</div>
                  <div className="tnum font-display text-head font-bold leading-none text-ink">
                    {est.on_target_share != null ? fmtPct(est.on_target_share) : '—'}
                  </div>
                </div>
                <p className="meta max-w-lg">
                  Share of estimated delivered reach falling in the countries this campaign targets
                  ({campaign.target_countries.join(', ')}).
                </p>
              </div>
            )}
            <CountryMap data={est.by_country} />
            <p className="meta mt-2">
              <strong className="text-ink-2">Estimate.</strong> No platform reports per-impression
              geography at post level. This is {est.basis} — a derivation from figures on this page,
              not a measurement of where impressions occurred.
            </p>
          </>
        )}
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
