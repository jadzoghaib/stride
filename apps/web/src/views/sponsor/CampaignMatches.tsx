import { ChevronDown, ChevronUp, Send } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Board } from '../../components/Board'
import { Avatar, CoverageChip, LoadError, Meter, Modal, PageLoading, Section, SimulatedChip, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney } from '../../lib/format'
import type { Campaign, Match, MatchesResponse } from '../../types'
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

/** What each component actually contributed to the score: component × the
 *  weight that was really applied. Sorted by that, because the panel exists to
 *  answer "what drove this match" — ranking by the raw component instead put
 *  the three smallest-weighted signals at the top. */
function decompose(m: Match) {
  const rows = Object.keys(m.weights).map((key) => {
    const value = m.components[key]
    const effective = m.effective_weights[key]
    return {
      key,
      value,
      effective,
      nominal: m.weights[key],
      contribution: value !== null && effective !== null ? value * effective : null,
    }
  })
  rows.sort((a, b) => (b.contribution ?? -1) - (a.contribution ?? -1))
  const top = Math.max(...rows.map((r) => r.contribution ?? 0), 0.0001)
  return { rows, top }
}

export default function CampaignMatches() {
  const { id } = useParams()
  const [data, setData] = useState<MatchesResponse | null>(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState<number | null>(null)
  const [offerFor, setOfferFor] = useState<Match | null>(null)

  /** POST, not GET. Opening the matches for a campaign is the exposure a later
   *  ranker learns from, and it is recorded here — but the server keys the
   *  record on the slate's own fingerprint, so a refresh or a second visit to
   *  an unchanged ranking is the same exposure rather than a duplicate training
   *  row. Reading without recording is still available on GET. */
  useEffect(() => {
    api
      .post<MatchesResponse>(`/api/campaigns/${id}/matches`)
      .then(setData)
      .catch((e) => setError(errorText(e)))
  }, [id])

  if (!data) return error ? <LoadError text={error} /> : <PageLoading />

  const c = data.campaign
  const best = data.matches[0]
  const fullCoverage = data.matches.filter(
    (m) => m.analytics_summary && m.analytics_summary.coverage.connected === m.analytics_summary.coverage.total,
  ).length

  return (
    <>
      <Board
        eyebrow={
          <Link to="/sponsor" className="hover:text-ink-2">
            Campaigns
          </Link>
        }
        title={c.name}
        tags={
          <>
            <span className="tag">{c.category}</span>
            <StatusChip status={c.status} />
            <SimulatedChip what="analytics" />
          </>
        }
        score={best ? best.score : null}
        scoreLabel="Best match"
        deltaNote={best ? best.display_name : 'no listed athletes match yet'}
        trendEmpty="Every score below decomposes into the components that produced it."
        figures={[
          { label: 'Ranked', value: data.matches.length },
          { label: 'Budget', value: `${fmtMoney(c.budget_eur_min)} – ${fmtMoney(c.budget_eur_max)}` },
          { label: 'Full analytics', value: `${fullCoverage} of ${data.matches.length}` },
        ]}
        footNote="audience fit computed against this campaign's own target"
      />

      <div>
        <Section title="Ranked matches" aside={<span className="meta">select a row for its score composition</span>}>
          <div className="space-y-2">
            {data.matches.map((m, idx) => (
              <div key={m.athlete_id} className="panel panel-hover">
                <button
                  className="flex w-full items-center gap-4 p-4 text-left"
                  aria-expanded={open === m.athlete_id}
                  onClick={() => setOpen(open === m.athlete_id ? null : m.athlete_id)}
                >
                  <span className="lane-no w-7 text-right">{idx + 1}</span>
                  <Avatar name={m.display_name} size={36} />
                  <div className="min-w-0">
                    <div className="font-display text-[15px] font-semibold uppercase tracking-board text-ink">
                      {m.display_name}
                    </div>
                    <div className="text-xs text-ink-3">
                      {m.sport} · {m.country} · rate {fmtMoney(m.base_rate_eur)}
                    </div>
                  </div>
                  <div className="ml-auto flex items-center gap-4">
                    <CoverageChip
                      coverage={m.analytics_summary ? { ...m.analytics_summary.coverage, list: [] } : null}
                    />
                    <div className="w-28">
                      <div className="tnum text-right font-display text-[26px] font-bold leading-none text-ink">
                        {m.score.toFixed(1)}
                      </div>
                      <div className="mt-1.5">
                        <Meter value={m.score} height={4} delay={idx * 40} />
                      </div>
                    </div>
                    {open === m.athlete_id ? (
                      <ChevronUp size={16} className="text-ink-3" />
                    ) : (
                      <ChevronDown size={16} className="text-ink-3" />
                    )}
                  </div>
                </button>

                {open === m.athlete_id && (
                  <div className="border-t border-line p-4">
                    <div className="grid gap-6 md:grid-cols-2">
                      <Composition match={m} />
                      <div>
                        <div className="cap mb-2">Why this match</div>
                        <ul className="space-y-1 text-sm text-ink-2">
                          {m.reasons.map((r) => (
                            <li key={r} className="flex gap-2">
                              <span className="text-ok" aria-hidden>
                                +
                              </span>
                              {r}
                            </li>
                          ))}
                          {m.caveats.map((r) => (
                            <li key={r} className="flex gap-2">
                              <span className="text-warn" aria-hidden>
                                !
                              </span>
                              {r}
                            </li>
                          ))}
                          {m.reasons.length + m.caveats.length === 0 && (
                            <li className="text-ink-3">No strong signals either way.</li>
                          )}
                        </ul>
                        <div className="mt-4 flex gap-2">
                          <button className="btn-go px-3 py-1.5 text-xs" onClick={() => setOfferFor(m)}>
                            <Send size={12} /> Send offer
                          </button>
                          <Link
                            to={`/sponsor/athletes/${m.slug}?campaign=${c.id}`}
                            className="btn px-3 py-1.5 text-xs"
                          >
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
      </div>

      {offerFor && <OfferDialog campaign={c} match={offerFor} onClose={() => setOfferFor(null)} />}
    </>
  )
}

function Composition({ match }: { match: Match }) {
  const { rows, top } = decompose(match)
  return (
    <div>
      <div className="cap mb-2">Score composition — ranked by contribution</div>
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <div key={r.key} className="grid grid-cols-[112px_1fr_42px_72px] items-center gap-2.5 text-xs">
            <span className="truncate text-ink-2">{COMPONENT_LABELS[r.key] ?? r.key}</span>
            {r.contribution === null ? (
              <span className="cap text-ink-3">not measured</span>
            ) : (
              <Meter
                value={(100 * r.contribution) / top}
                height={8}
                delay={i * 45}
                muted={r.contribution < top / 2}
              />
            )}
            <span className="tnum text-right font-display text-[15px] font-bold text-ink">
              {r.contribution === null ? '—' : (100 * r.contribution).toFixed(1)}
            </span>
            <span className="meta text-right">
              {r.value === null
                ? 'excluded'
                : `${(100 * r.value).toFixed(0)} × ${(100 * (r.effective ?? 0)).toFixed(0)}%`}
            </span>
          </div>
        ))}
      </div>
      <div className="meta mt-2.5">
        Bar length is each component's contribution to the {match.score.toFixed(1)} — component × the
        weight actually applied, not the component alone.
      </div>
    </div>
  )
}

function OfferDialog({ campaign, match, onClose }: { campaign: Campaign; match: Match; onClose: () => void }) {
  const [form, setForm] = useState({
    deal_type: campaign.deal_types[0] ?? 'social_post',
    amount_eur: Math.min(match.base_rate_eur, campaign.budget_eur_max),
    message: '',
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await api.post(`/api/campaigns/${campaign.id}/offers`, { athlete_id: match.athlete_id, ...form })
      setDone(true)
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={done ? 'Offer sent' : `Offer — ${match.display_name}`} onClose={onClose}>
      {(close) => (done ? (
        <div>
          <p className="text-sm text-ink-2">
            {match.display_name} will see this in their deal inbox and can accept or decline. Track it in
            your pipeline.
          </p>
          <button className="btn-go mt-4" onClick={close}>
            Close
          </button>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <label className="block">
            <span className="cap">Deal format</span>
            <select
              className="field mt-1"
              value={form.deal_type}
              onChange={(e) => setForm((f) => ({ ...f, deal_type: e.target.value }))}
            >
              {(campaign.deal_types.length ? campaign.deal_types : ['social_post']).map((t) => (
                <option key={t} value={t}>
                  {dealTypeLabel(t)}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="cap">Amount (EUR)</span>
            <input
              className="field mt-1 tnum"
              type="number"
              min={1}
              value={form.amount_eur}
              onChange={(e) => setForm((f) => ({ ...f, amount_eur: Number(e.target.value) }))}
            />
            <span className="mt-1 block text-xs text-ink-3">
              Athlete rate card: {fmtMoney(match.base_rate_eur)} · campaign budget up to{' '}
              {fmtMoney(campaign.budget_eur_max)}
            </span>
          </label>
          <label className="block">
            <span className="cap">Message</span>
            <textarea
              className="field mt-1 min-h-20"
              value={form.message}
              onChange={(e) => setForm((f) => ({ ...f, message: e.target.value }))}
            />
          </label>
          {error && <div className="text-sm text-critical">{error}</div>}
          <div className="flex gap-2">
            <button className="btn-go" disabled={busy}>
              {busy ? 'Sending…' : 'Send offer'}
            </button>
            <button type="button" className="btn" onClick={close}>
              Cancel
            </button>
          </div>
        </form>
      ))}
    </Modal>
  )
}
