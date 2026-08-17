import { useEffect, useState } from 'react'
import { LoadError, PageHeader, PageLoading, EmptyNote, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney } from '../../lib/format'
import type { AthleteWorkspace, Deal } from '../../types'
import { dealTypeLabel } from '../../types'

export default function AthleteDeals() {
  const [deals, setDeals] = useState<Deal[] | null>(null)
  const [error, setError] = useState('')

  const load = () =>
    api.get<AthleteWorkspace>('/api/athlete/workspace').then((ws) => setDeals(ws.deals)).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    // deep links from dashboard stats (e.g. /athlete/deals#history)
    if (deals && window.location.hash) {
      document.querySelector(window.location.hash)?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [deals])

  const respond = async (id: number, action: 'accept' | 'decline') => {
    setError('')
    try {
      await api.post(`/api/athlete/deals/${id}/respond`, { action })
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!deals) return error ? <LoadError text={error} /> : <PageLoading />

  const open = deals.filter((d) => d.status === 'offered')
  const history = deals.filter((d) => d.status !== 'offered')

  return (
    <div>
      <PageHeader
        eyebrow="Athlete"
        title="Deals"
        lede="Offers waiting on you, and every offer already resolved."
        aside={<span className="meta">{open.length} awaiting response</span>}
      />
      {error && <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">{error}</div>}

      <Section title={`Open offers (${open.length})`}>
        {open.length === 0 && <EmptyNote text="No open offers. Sponsors find you through campaign matching — a complete profile and connected platforms raise your visibility." />}
        <div className="space-y-3">
          {open.map((d) => (
            <div key={d.id} className="panel p-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-lg font-semibold tnum text-ink">{fmtMoney(d.amount_usd)}</span>
                <span className="tag">{dealTypeLabel(d.deal_type)}</span>
                <span className="text-sm text-ink-2">{d.org_name} — {d.campaign_name}</span>
                <span className="ml-auto text-xs text-ink-3">{fmtDate(d.created_at)}</span>
              </div>
              {d.message && <p className="mt-2 text-sm text-ink-2">{d.message}</p>}
              <div className="mt-4 flex gap-2">
                <button className="btn-go" onClick={() => respond(d.id, 'accept')}>Accept</button>
                <button className="btn" onClick={() => respond(d.id, 'decline')}>Decline</button>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="History" id="history">
        {history.length === 0 ? (
          <EmptyNote text="No deal history yet." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Sponsor</th>
                <th className="table-head">Campaign</th>
                <th className="table-head">Format</th>
                <th className="table-head text-right">Amount</th>
                <th className="table-head">Status</th>
                <th className="table-head">Resolved</th>
              </tr>
            </thead>
            <tbody>
              {history.map((d) => (
                <tr key={d.id}>
                  <td className="table-cell text-ink">{d.org_name}</td>
                  <td className="table-cell">{d.campaign_name}</td>
                  <td className="table-cell">{dealTypeLabel(d.deal_type)}</td>
                  <td className="table-cell tnum text-right">{fmtMoney(d.amount_usd)}</td>
                  <td className="table-cell"><StatusChip status={d.status} /></td>
                  <td className="table-cell text-xs text-ink-3">{fmtDate(d.responded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </div>
  )
}
