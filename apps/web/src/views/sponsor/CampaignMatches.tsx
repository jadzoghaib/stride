import { ChevronDown, ChevronUp, Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { LoadError, PageLoading, Avatar, CoverageChip, Meter, Section } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney } from '../../lib/format'
import type { Campaign, Match } from '../../types'
import { dealTypeLabel } from '../../types'

const COMPONENT_LABELS: Record<string, string> = {
  audience_fit: 'Audience fit',
  engagement_quality: 'Engagement quality',
  audience_scale: 'Audience scale',
  growth: 'Growth',
  consistency: 'Consistency',
  budget_alignment: 'Budget alignment',
  deal_type_overlap: 'Format overlap',
  category_affinity: 'Category affinity',
}

export default function CampaignMatches() {
  const { id } = useParams()
  const [data, setData] = useState<{ campaign: Campaign; matches: Match[] } | null>(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState<number | null>(null)
  const [offerFor, setOfferFor] = useState<Match | null>(null)

  useEffect(() => {
    api.get<{ campaign: Campaign; matches: Match[] }>(`/api/campaigns/${id}/matches`)
      .then(setData).catch((e) => setError(errorText(e)))
  }, [id])

  if (!data) return error ? <LoadError text={error} /> : <PageLoading />

  const c = data.campaign
  return (
    <div>
      <div className="text-xs text-mist-400"><Link to="/sponsor" className="hover:text-mist-200">Campaigns</Link> / matches</div>
      <div className="mt-1 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-mist-100">{c.name}</h1>
        <span className="chip">{c.category}</span>
        <span className="tnum text-sm text-mist-300">{fmtMoney(c.budget_usd_min)} – {fmtMoney(c.budget_usd_max)}</span>
      </div>
      <p className="mt-1 text-sm text-mist-400">
        {data.matches.length} athletes ranked against this brief. Audience fit is computed against this campaign's
        target — every score decomposes into its components below.
      </p>

      <Section title="Ranked matches">
        <div className="space-y-2">
          {data.matches.map((m, idx) => (
            <div key={m.athlete_id} className="panel panel-hover">
              <button className="flex w-full items-center gap-4 p-4 text-left"
                      onClick={() => setOpen(open === m.athlete_id ? null : m.athlete_id)}>
                <span className="tnum w-6 text-right text-mist-400">{idx + 1}</span>
                <Avatar name={m.display_name} size={36} />
                <div className="min-w-0">
                  <div className="font-medium text-mist-100">{m.display_name}</div>
                  <div className="text-xs text-mist-400">{m.sport} · {m.country} · rate {fmtMoney(m.base_rate_usd)}</div>
                </div>
                <div className="ml-auto flex items-center gap-4">
                  <CoverageChip coverage={m.analytics_summary ? { ...m.analytics_summary.coverage, list: [] } : null} />
                  <div className="w-28">
                    <div className="tnum text-right text-lg font-semibold text-mist-100">{m.score.toFixed(1)}</div>
                    <Meter value={m.score} height={4} />
                  </div>
                  {open === m.athlete_id ? <ChevronUp size={16} className="text-mist-400" /> : <ChevronDown size={16} className="text-mist-400" />}
                </div>
              </button>

              {open === m.athlete_id && (
                <div className="border-t border-line p-4">
                  <div className="grid gap-6 md:grid-cols-2">
                    <div>
                      <div className="microcaps mb-2">Score composition (weight × component)</div>
                      <div className="space-y-1.5">
                        {Object.entries(m.components).map(([k, v]) => (
                          <div key={k} className="grid grid-cols-[150px_1fr_72px] items-center gap-2 text-xs">
                            <span className="text-mist-300">{COMPONENT_LABELS[k] ?? k}</span>
                            <div className="h-2 rounded-sm bg-ink-800 overflow-hidden">
                              <div className="h-full wave-line rounded-sm" style={{ width: `${100 * v}%` }} />
                            </div>
                            <span className="tnum text-right text-mist-400">{(100 * v).toFixed(0)} × {(m.weights[k] * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="microcaps mb-2">Why this match</div>
                      <ul className="space-y-1 text-sm text-mist-300">
                        {m.reasons.map((r) => <li key={r} className="flex gap-2"><span className="text-ok">+</span>{r}</li>)}
                        {m.caveats.map((r) => <li key={r} className="flex gap-2"><span className="text-warn">!</span>{r}</li>)}
                        {m.reasons.length + m.caveats.length === 0 && <li className="text-mist-400">No strong signals either way.</li>}
                      </ul>
                      <div className="mt-4 flex gap-2">
                        <button className="btn-primary px-3 py-1.5 text-xs" onClick={() => setOfferFor(m)}>
                          <Send size={12} /> Send offer
                        </button>
                        <Link to={`/sponsor/athletes/${m.slug}?campaign=${c.id}`} className="btn px-3 py-1.5 text-xs">
                          Full analytics
                        </Link>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </Section>

      {offerFor && <OfferDialog campaign={c} match={offerFor} onClose={() => setOfferFor(null)} />}
    </div>
  )
}

function OfferDialog({ campaign, match, onClose }: { campaign: Campaign; match: Match; onClose: () => void }) {
  const [form, setForm] = useState({
    deal_type: campaign.deal_types[0] ?? 'social_post',
    amount_usd: Math.min(match.base_rate_usd, campaign.budget_usd_max),
    message: '',
  })
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.post(`/api/campaigns/${campaign.id}/offers`, { athlete_id: match.athlete_id, ...form })
      setDone(true)
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-ink-950/80 p-4" onClick={onClose}>
      <div className="panel w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
        {done ? (
          <div>
            <h3 className="font-medium text-mist-100">Offer sent</h3>
            <p className="mt-2 text-sm text-mist-300">
              {match.display_name} will see this in their deal inbox and can accept or decline. Track it in your pipeline.
            </p>
            <button className="btn-primary mt-4" onClick={onClose}>Close</button>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <h3 className="font-medium text-mist-100">Offer — {match.display_name}</h3>
            <label className="block"><span className="microcaps">Deal format</span>
              <select className="field mt-1" value={form.deal_type}
                      onChange={(e) => setForm((f) => ({ ...f, deal_type: e.target.value }))}>
                {(campaign.deal_types.length ? campaign.deal_types : ['social_post']).map((t) => (
                  <option key={t} value={t}>{dealTypeLabel(t)}</option>
                ))}
              </select></label>
            <label className="block"><span className="microcaps">Amount (USD)</span>
              <input className="field mt-1 tnum" type="number" min={1} value={form.amount_usd}
                     onChange={(e) => setForm((f) => ({ ...f, amount_usd: Number(e.target.value) }))} />
              <span className="mt-1 block text-xs text-mist-400">
                Athlete rate card: {fmtMoney(match.base_rate_usd)} · campaign budget up to {fmtMoney(campaign.budget_usd_max)}
              </span></label>
            <label className="block"><span className="microcaps">Message</span>
              <textarea className="field mt-1 min-h-20" value={form.message}
                        onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))} /></label>
            {error && <div className="text-sm text-danger">{error}</div>}
            <div className="flex gap-2">
              <button className="btn-primary">Send offer</button>
              <button type="button" className="btn" onClick={onClose}>Cancel</button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
