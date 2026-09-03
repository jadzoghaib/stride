import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Delta, EmptyNote, KV, LoadError, Meter, PageHeader, PageLoading, Section, SimulatedChip, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney, fmtNum, fmtPct } from '../../lib/format'
import type { Commitment, Deal, DealPerformance } from '../../types'
import { dealTypeLabel, platformLabel } from '../../types'

const STAGES: Deal['status'][] = ['offered', 'accepted', 'completed', 'declined', 'withdrawn']

export default function SponsorPipeline({ campaignId, embedded = false }: {
  /** Scope every stage to one campaign. A pipeline is a per-campaign question
   *  far more often than a company-wide one — "how is the spring line going"
   *  rather than "show me every offer this org has ever sent". */
  campaignId?: number
  /** Suppress the page header when this is a tab inside a campaign, which
   *  already says which campaign you are looking at. */
  embedded?: boolean
} = {}) {
  const [deals, setDeals] = useState<Deal[] | null>(null)
  const [commitments, setCommitments] = useState<Commitment[]>([])
  const [error, setError] = useState('')
  const [openPerf, setOpenPerf] = useState<number | null>(null)

  const load = () =>
    api.get<{ deals: Deal[]; club_commitments: Commitment[] }>('/api/sponsor/workspace')
      .then((ws) => {
        setDeals(campaignId ? ws.deals.filter((d) => d.campaign_id === campaignId) : ws.deals)
        // Club packages are bought by the org, not by a campaign, so a campaign
        // view has none to show rather than showing all of them under the
        // wrong heading.
        setCommitments(campaignId ? [] : (ws.club_commitments ?? []))
      })
      .catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [campaignId])

  const cancelCommitment = async (id: number) => {
    try {
      await api.post(`/api/commitments/${id}/cancel`)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  const withdraw = async (id: number) => {
    try {
      await api.post(`/api/deals/${id}/withdraw`)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!deals) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      {!embedded && (
        <PageHeader
          eyebrow="Sponsor"
          title="Deal pipeline"
          lede="Every offer this organization has sent, by stage, plus the club packages it backs."
          aside={<span className="meta">{deals.length} deal{deals.length === 1 ? '' : 's'}</span>}
        />
      )}
      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}
      {STAGES.map((stage) => {
        const list = deals.filter((d) => d.status === stage)
        if (!list.length) return null
        return (
          <Section key={stage} title={`${stage} (${list.length})`}>
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="table-head">Athlete</th>
                  {!campaignId && <th className="table-head">Campaign</th>}
                  <th className="table-head">Format</th>
                  <th className="table-head text-right">Amount</th>
                  <th className="table-head">Created</th>
                  <th className="table-head" />
                </tr>
              </thead>
              <tbody>
                {list.map((d) => (
                  <Fragment key={d.id}>
                    <tr>
                      <td className="table-cell">
                        <Link to={`/sponsor/athletes/${d.athlete_slug}`} className="text-ink hover:text-accent">
                          {d.athlete_name}
                        </Link>
                        <span className="ml-2 text-xs text-ink-3">{d.sport}</span>
                      </td>
                      {!campaignId && <td className="table-cell">{d.campaign_name}</td>}
                      <td className="table-cell">{dealTypeLabel(d.deal_type)}</td>
                      <td className="table-cell tnum text-right">{fmtMoney(d.amount_eur)}</td>
                      <td className="table-cell text-xs text-ink-3">{fmtDate(d.created_at)}</td>
                      <td className="table-cell text-right">
                        {d.status === 'offered' && (
                          <button className="btn px-2.5 py-1 text-xs" onClick={() => withdraw(d.id)}>Withdraw</button>
                        )}
                        {(d.status === 'accepted' || d.status === 'completed') && (
                          <button
                            className="btn px-2.5 py-1 text-xs"
                            aria-expanded={openPerf === d.id}
                            onClick={() => setOpenPerf(openPerf === d.id ? null : d.id)}
                          >
                            {openPerf === d.id
                              ? 'Hide'
                              : d.status === 'completed' ? 'What we got' : 'Delivery status'}
                          </button>
                        )}
                      </td>
                    </tr>
                    {openPerf === d.id && (
                      <tr>
                        <td className="table-cell" colSpan={6}>
                          <Performance dealId={d.id} />
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </Section>
        )
      })}
      {deals.length === 0 && <div className="mt-6"><EmptyNote text="No deals yet — run matching on a campaign and send your first offer." /></div>}

      <Section title={`Club sponsorships (${commitments.filter((c) => c.status === 'active').length} active)`}>
        {commitments.length === 0 ? (
          <EmptyNote text="No club packages backed yet — browse Clubs to support a club or an individual player through their club." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Club</th>
                <th className="table-head">Package</th>
                <th className="table-head">Player</th>
                <th className="table-head text-right">Amount</th>
                <th className="table-head">Status</th>
                <th className="table-head" />
              </tr>
            </thead>
            <tbody>
              {commitments.map((c) => (
                <tr key={c.id}>
                  <td className="table-cell">
                    <Link to={`/clubs/${c.club_slug}`} className="text-ink hover:text-accent">{c.club_name}</Link>
                  </td>
                  <td className="table-cell">{c.package_name}
                    {c.package_type === 'player_direct' && <span className="tag ml-2 border-accent text-ink">player-direct</span>}
                  </td>
                  <td className="table-cell">{c.athlete_name ?? '—'}</td>
                  <td className="table-cell tnum text-right">{fmtMoney(c.amount_eur)}</td>
                  <td className="table-cell"><StatusChip status={c.status} /></td>
                  <td className="table-cell text-right">
                    {c.status === 'active' && (
                      <button className="btn px-2.5 py-1 text-xs" onClick={() => cancelCommitment(c.id)}>Cancel</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  )
}

/** What the campaign actually delivered, against the projection captured when
 *  the offer was sent.
 *
 *  Every headline figure opens to the posts underneath it — the same rule the
 *  marketability scores follow. A figure a sponsor cannot decompose is one they
 *  have to take on trust, and taking marketing numbers on trust is the thing
 *  this product exists not to ask of them. */
function Performance({ dealId }: { dealId: number }) {
  const [perf, setPerf] = useState<DealPerformance | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<DealPerformance>(`/api/deals/${dealId}/performance`)
      .then(setPerf)
      .catch((e) => setError(errorText(e)))
  }, [dealId])

  if (error) return <p className="py-2 text-sm text-critical">{error}</p>
  if (!perf) return <p className="meta py-2">Loading result…</p>

  const { delivered, projected } = perf
  // both sides have to exist: `100 * null` is 0, which would draw a full-width
  // "0% of projection" meter for a deal that simply has not been posted yet
  const hit = projected.reach && delivered.reach !== null
    ? (100 * delivered.reach) / projected.reach
    : null

  return (
    <div className="py-3">
      <div className="flex flex-wrap items-baseline gap-x-8 gap-y-2.5">
        <KV label="Delivered reach" value={fmtNum(delivered.reach)} />
        <SimulatedChip what="delivery" />
        <KV label="Projected at offer" value={fmtNum(projected.reach)} />
        <KV label="Engagements" value={fmtNum(delivered.engagements)} />
        {/* None, not zero: an unmeasured campaign must not read as a free one */}
        <KV label="Cost / 1k reach" value={perf.cost_per_1k_reach === null ? '—' : fmtMoney(perf.cost_per_1k_reach)} />
        <KV label="Cost / engagement" value={perf.cost_per_engagement === null ? '—' : fmtMoney(perf.cost_per_engagement)} />
        <div className="flex items-baseline gap-2.5">
          <span className="cap">vs projection</span>
          <Delta value={perf.variance_pct} />
        </div>
      </div>

      {hit !== null && (
        <div className="mt-3 max-w-md">
          <Meter value={hit} height={6} muted={hit < 100} />
          <span className="meta mt-1 block">
            {fmtPct(hit / 100, 0)} of the reach projected when the offer was sent
          </span>
        </div>
      )}

      {perf.deliverables.length === 0 ? (
        <p className="meta mt-3">
          {perf.deal.status === 'completed'
            ? 'Marked complete with nothing attached — there is no measurement to show.'
            : 'The athlete has not attached a post yet. Figures appear here as soon as they do.'}
        </p>
      ) : (
        <table className="mt-4 w-full text-xs">
          <thead>
            <tr>
              <th className="table-head">Platform</th>
              <th className="table-head">Post</th>
              <th className="table-head">Published</th>
              <th className="table-head text-right">Reach</th>
              <th className="table-head text-right">Engagement</th>
            </tr>
          </thead>
          <tbody>
            {perf.deliverables.map((d) => (
              <tr key={d.post_id}>
                <td className="table-cell">{platformLabel(d.platform)}</td>
                <td className="table-cell max-w-72 truncate text-ink">
                  <a href={d.permalink} target="_blank" rel="noreferrer" className="hover:text-accent">
                    {d.title}
                  </a>
                </td>
                <td className="table-cell text-ink-3">{fmtDate(d.published_at)}</td>
                <td className="table-cell tnum text-right">{fmtNum(d.reach)}</td>
                <td className="table-cell tnum text-right">{fmtPct(d.engagement_rate, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
