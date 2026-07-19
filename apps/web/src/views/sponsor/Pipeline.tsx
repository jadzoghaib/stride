import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LoadError, PageLoading, EmptyNote, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney } from '../../lib/format'
import type { Commitment, Deal } from '../../types'
import { dealTypeLabel } from '../../types'

const STAGES: Deal['status'][] = ['offered', 'accepted', 'completed', 'declined', 'withdrawn']

export default function SponsorPipeline() {
  const [deals, setDeals] = useState<Deal[] | null>(null)
  const [commitments, setCommitments] = useState<Commitment[]>([])
  const [error, setError] = useState('')

  const load = () =>
    api.get<{ deals: Deal[]; club_commitments: Commitment[] }>('/api/sponsor/workspace')
      .then((ws) => { setDeals(ws.deals); setCommitments(ws.club_commitments ?? []) })
      .catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [])

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
      <h1 className="text-2xl font-semibold text-mist-100">Deal pipeline</h1>
      {error && <div className="mt-3 text-sm text-danger">{error}</div>}
      {STAGES.map((stage) => {
        const list = deals.filter((d) => d.status === stage)
        if (!list.length) return null
        return (
          <Section key={stage} title={`${stage} (${list.length})`}>
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="table-head">Athlete</th>
                  <th className="table-head">Campaign</th>
                  <th className="table-head">Format</th>
                  <th className="table-head text-right">Amount</th>
                  <th className="table-head">Created</th>
                  <th className="table-head" />
                </tr>
              </thead>
              <tbody>
                {list.map((d) => (
                  <tr key={d.id}>
                    <td className="table-cell">
                      <Link to={`/sponsor/athletes/${d.athlete_slug}`} className="text-mist-100 hover:text-pulse-400">
                        {d.athlete_name}
                      </Link>
                      <span className="ml-2 text-xs text-mist-400">{d.sport}</span>
                    </td>
                    <td className="table-cell">{d.campaign_name}</td>
                    <td className="table-cell">{dealTypeLabel(d.deal_type)}</td>
                    <td className="table-cell tnum text-right">{fmtMoney(d.amount_usd)}</td>
                    <td className="table-cell text-xs text-mist-400">{fmtDate(d.created_at)}</td>
                    <td className="table-cell text-right">
                      {d.status === 'offered' && (
                        <button className="btn px-2.5 py-1 text-xs" onClick={() => withdraw(d.id)}>Withdraw</button>
                      )}
                    </td>
                  </tr>
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
                    <Link to={`/clubs/${c.club_slug}`} className="text-mist-100 hover:text-pulse-400">{c.club_name}</Link>
                  </td>
                  <td className="table-cell">{c.package_name}
                    {c.package_type === 'player_direct' && <span className="chip ml-2 border-pulse-500 text-mist-100">player-direct</span>}
                  </td>
                  <td className="table-cell">{c.athlete_name ?? '—'}</td>
                  <td className="table-cell tnum text-right">{fmtMoney(c.amount_usd)}</td>
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
