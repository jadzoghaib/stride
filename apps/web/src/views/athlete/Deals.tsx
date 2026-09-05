import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LoadError, Modal, PageHeader, PageLoading, EmptyNote, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney, fmtNum } from '../../lib/format'
import { disclosure } from '../../lib/legal'
import type { AthletePost, AthleteWorkspace, Deal } from '../../types'
import { dealTypeLabel, platformLabel } from '../../types'

export default function AthleteDeals() {
  const navigate = useNavigate()
  const [ws, setWs] = useState<AthleteWorkspace | null>(null)
  const [error, setError] = useState('')
  const [delivering, setDelivering] = useState<Deal | null>(null)
  const [detail, setDetail] = useState<Deal | null>(null)
  const [asking, setAsking] = useState<Deal | null>(null)

  const load = () =>
    api.get<AthleteWorkspace>('/api/athlete/workspace').then(setWs).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [])

  useEffect(() => {
    // deep links from dashboard stats (e.g. /athlete/deals#history)
    if (ws && window.location.hash) {
      document.querySelector(window.location.hash)?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [ws])

  const respond = async (id: number, action: 'accept' | 'decline') => {
    setError('')
    try {
      await api.post(`/api/athlete/deals/${id}/respond`, { action })
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  /** Open a thread with the sponsor and drop the athlete into it.
   *
   *  The offer is quoted into the first message on purpose: a sponsor running
   *  several campaigns should not have to guess which one "quick question" is
   *  about, and the athlete should not have to retype it. */
  const ask = async (d: Deal, body: string) => {
    setError('')
    try {
      await api.post('/api/messages', { to_user: d.org_user_id, body })
      setAsking(null)
      navigate('/inbox')
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!ws) return error ? <LoadError text={error} /> : <PageLoading />

  const deals = ws.deals
  const open = deals.filter((d) => d.status === 'offered')
  const accepted = deals.filter((d) => d.status === 'accepted')
  const history = deals.filter((d) => d.status !== 'offered' && d.status !== 'accepted')
  const rules = disclosure(ws.editable.country)

  return (
    <div>
      <PageHeader
        eyebrow="Athlete"
        title="Deals"
        lede="Offers waiting on you, the work in progress, and every offer already resolved."
        aside={<span className="meta">{open.length} awaiting response</span>}
      />
      {error && <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">{error}</div>}

      <Section title={`Open offers (${open.length})`}>
        {open.length === 0 && <EmptyNote text="No open offers. Sponsors find you through campaign matching — a complete profile and connected platforms raise your visibility." />}
        <div className="space-y-3">
          {open.map((d) => (
            <div key={d.id} className="panel p-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="text-lg font-semibold tnum text-ink">{fmtMoney(d.amount_eur)}</span>
                <span className="tag">{dealTypeLabel(d.deal_type)}</span>
                <span className="text-sm text-ink-2">{d.org_name} — {d.campaign_name}</span>
                <span className="ml-auto text-xs text-ink-3">{fmtDate(d.created_at)}</span>
              </div>
              {d.message && <p className="mt-2 text-sm text-ink-2">{d.message}</p>}

              {/* Accept and Decline were the only two things an athlete could do
                  with an offer, which made a commercial negotiation a yes/no
                  prompt. Details is what informs the answer; Ask a question is
                  the third answer people actually give. */}
              <div className="mt-4 flex flex-wrap gap-2">
                <button className="btn-go" onClick={() => respond(d.id, 'accept')}>Accept</button>
                <button className="btn" onClick={() => respond(d.id, 'decline')}>Decline</button>
                <button className="btn" onClick={() => setDetail(d)}>See details</button>
                {d.org_user_id != null && (
                  <button className="btn" onClick={() => setAsking(d)}>Ask a question</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section
        title={`Delivering (${accepted.length})`}
        aside={<span className="meta">accepted, not yet delivered</span>}
      >
        {accepted.length === 0 ? (
          <EmptyNote text="Nothing in progress. An accepted offer stays here until you attach what you posted." />
        ) : (
          <>
            <DisclosureNote rules={rules} />
            <div className="mt-3 space-y-3">
              {accepted.map((d) => {
                const attached = d.deliverable_post_ids?.length ?? 0
                return (
                  <div key={d.id} className="panel p-5">
                    <div className="flex flex-wrap items-center gap-3">
                      <span className="text-lg font-semibold tnum text-ink">{fmtMoney(d.amount_eur)}</span>
                      <span className="tag">{dealTypeLabel(d.deal_type)}</span>
                      <span className="text-sm text-ink-2">{d.org_name} — {d.campaign_name}</span>
                      <button className="btn-go ml-auto" onClick={() => setDelivering(d)}>
                        {attached ? 'Review and deliver' : 'Attach what you posted'}
                      </button>
                    </div>
                    <p className="meta mt-2">
                      {attached
                        ? `${attached} post${attached === 1 ? '' : 's'} attached. The sponsor sees their reach once you mark the deal delivered.`
                        : 'Attaching the post you published is what lets the sponsor see the result — and it is the record that earns you the next offer.'}
                    </p>
                  </div>
                )
              })}
            </div>
          </>
        )}
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
                  <td className="table-cell tnum text-right">{fmtMoney(d.amount_eur)}</td>
                  <td className="table-cell"><StatusChip status={d.status} /></td>
                  {/* a completed deal resolved when it was delivered, not when it
                      was accepted — the older column would misdate it */}
                  <td className="table-cell text-xs text-ink-3">{fmtDate(d.completed_at ?? d.responded_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {delivering && (
        <DeliverDialog
          deal={delivering}
          rules={rules}
          // Attaching writes to the server but only advanced the dialog's own
          // state, so closing without delivering left the card behind still
          // reading "Attach what you posted" over a post that was attached.
          onAttach={() => void load()}
          onClose={() => setDelivering(null)}
          onDone={() => {
            setDelivering(null)
            void load()
          }}
        />
      )}

      {detail && <OfferDetail deal={detail} onClose={() => setDetail(null)} />}
      {asking && (
        <AskDialog deal={asking} onClose={() => setAsking(null)}
                   onSend={(body) => void ask(asking, body)} />
      )}
    </div>
  )
}

/** Everything the offer is, on one screen.
 *
 *  An offer is a commercial proposal, and the card in the list is its headline.
 *  This is the rest: who is asking, what the campaign is trying to do, who they
 *  are trying to reach, and what reach was projected when the price was set.
 *  None of it is new data -- it was all sitting in `campaigns` and never sent.
 */
function OfferDetail({ deal, onClose }: { deal: Deal; onClose: () => void }) {
  const targets: [string, string[]][] = [
    ['Countries', deal.target_countries ?? []],
    ['Age', deal.target_age_buckets ?? []],
    ['Gender', deal.target_genders ?? []],
    ['Topics', deal.target_topics ?? []],
  ]
  const anyTarget = targets.some(([, v]) => v.length > 0)

  return (
    <Modal title={`${deal.org_name ?? 'Offer'} — ${deal.campaign_name ?? ''}`} onClose={onClose} wide>
      {() => (
        <div className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <Fact label="Fee" value={fmtMoney(deal.amount_eur)} strong />
            <Fact label="Format" value={dealTypeLabel(deal.deal_type)} />
            <Fact label="Offered" value={fmtDate(deal.created_at)} />
            {/* fmtNum renders an absent projection as a dash. It is captured at
                offer time, so an older offer legitimately has none -- and a 0
                here would read as "they expect this to reach nobody". */}
            <Fact label="Projected reach at offer" value={fmtNum(deal.projected_reach ?? null)} />
            <Fact label="Campaign budget"
                  value={deal.budget_eur_min != null && deal.budget_eur_max != null
                    ? `${fmtMoney(deal.budget_eur_min)} – ${fmtMoney(deal.budget_eur_max)}`
                    : '—'} />
            <Fact label="Category" value={deal.category || '—'} />
          </div>

          {deal.objective && (
            <div>
              <h4 className="cap mb-1.5 text-ink-3">What the campaign is for</h4>
              <p className="text-sm text-ink-2">{deal.objective}</p>
            </div>
          )}

          {deal.message && (
            <div>
              <h4 className="cap mb-1.5 text-ink-3">Their note to you</h4>
              <p className="whitespace-pre-line rounded border border-line bg-raised px-3 py-2.5 text-sm text-ink-2">
                {deal.message}
              </p>
            </div>
          )}

          {anyTarget && (
            <div>
              <h4 className="cap mb-1.5 text-ink-3">Who they are trying to reach</h4>
              <div className="space-y-2">
                {targets.filter(([, v]) => v.length > 0).map(([label, values]) => (
                  <div key={label} className="flex flex-wrap items-baseline gap-2">
                    <span className="meta w-20 shrink-0">{label}</span>
                    {values.map((v) => <span key={v} className="tag">{v}</span>)}
                  </div>
                ))}
              </div>
              <p className="meta mt-2">
                Your audience is measured against this — it is what the match score was built from.
              </p>
            </div>
          )}

          <div>
            <h4 className="cap mb-1.5 text-ink-3">Sponsor</h4>
            <p className="text-sm text-ink-2">
              {deal.org_name}{deal.org_industry ? ` · ${deal.org_industry}` : ''}
              {deal.org_website && (
                <>
                  {' · '}
                  <a href={deal.org_website} target="_blank" rel="noreferrer noopener"
                     className="text-accent hover:underline">{deal.org_website}</a>
                </>
              )}
            </p>
          </div>
        </div>
      )}
    </Modal>
  )
}

function Fact({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return (
    <div className="rounded border border-line bg-raised px-3 py-2.5">
      <div className="cap text-ink-3">{label}</div>
      <div className={`tnum mt-0.5 ${strong ? 'font-display text-lead font-bold text-ink' : 'text-sm text-ink-2'}`}>
        {value}
      </div>
    </div>
  )
}

/** Reply with a sentence instead of a verdict.
 *
 *  The offer is quoted into the draft rather than merely referenced, because a
 *  sponsor running four campaigns reading "quick question about the rate" has
 *  no idea which one it is about. */
function AskDialog({ deal, onClose, onSend }: {
  deal: Deal
  onClose: () => void
  onSend: (body: string) => void
}) {
  const quote = `Re: ${deal.campaign_name} — ${fmtMoney(deal.amount_eur)}, ${dealTypeLabel(deal.deal_type)}

`
  const [body, setBody] = useState(quote)

  return (
    <Modal title={`Ask ${deal.org_name ?? 'the sponsor'} a question`} onClose={onClose}>
      {(close) => (
        <div className="space-y-3">
          <p className="meta">
            This opens a thread in your inbox. The offer stays open — asking is not answering.
          </p>
          <textarea className="field min-h-[9rem] w-full" value={body} autoFocus
                    onChange={(e) => setBody(e.target.value)} />
          <div className="flex justify-end gap-2">
            <button className="btn" onClick={close}>Cancel</button>
            <button className="btn-go" disabled={body.trim().length <= quote.trim().length}
                    onClick={() => onSend(body.trim())}>
              Send
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}

/** The disclosure duty, stated where the posting happens. It is the athlete's,
 *  not Stride's — see the Terms — which is exactly why a marketplace that never
 *  mentions it is not doing them a favour. */
function DisclosureNote({ rules }: { rules: ReturnType<typeof disclosure> }) {
  return (
    <div className="rounded border border-warn/40 bg-warn/10 px-3.5 py-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="cap text-ink-2">Disclose the post</span>
        {rules.tags.map((t) => (
          <span key={t} className="tag">{t}</span>
        ))}
        {rules.fallback && <span className="cap text-ink-2">default wording</span>}
      </div>
      {/* ink-2, not .meta's ink-3: this sits on a 10%% warn tint rather than the
          flat panel, where ink-3 measures 4.38:1 dark / 4.04:1 light — under AA. */}
      <p className="meta mt-1.5 text-ink-2">{rules.note}</p>
    </div>
  )
}

/** Attaching a post is what turns a finished deal into a measured one. The
 *  server refuses completion until at least one is attached, so this dialog is
 *  the only route from `accepted` to `completed`. */
function DeliverDialog({
  deal,
  rules,
  onAttach,
  onClose,
  onDone,
}: {
  deal: Deal
  rules: ReturnType<typeof disclosure>
  onAttach: () => void
  onClose: () => void
  onDone: () => void
}) {
  const [posts, setPosts] = useState<AthletePost[] | null>(null)
  const [attached, setAttached] = useState<number[]>(deal.deliverable_post_ids ?? [])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get<AthletePost[]>('/api/athlete/posts').then(setPosts).catch((e) => setError(errorText(e)))
  }, [])

  const attach = async (postId: number) => {
    setError('')
    setBusy(true)
    try {
      await api.post(`/api/athlete/deals/${deal.id}/deliverables`, { post_id: postId })
      setAttached((a) => [...a, postId])
      onAttach()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  const complete = async (close: () => void) => {
    setError('')
    setBusy(true)
    try {
      await api.post(`/api/athlete/deals/${deal.id}/complete`)
      close()
      onDone()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={`Deliver — ${deal.org_name ?? 'deal'}`} onClose={onClose} wide>
      {(close) => (
        <>
          <p className="text-sm text-ink-2">
            Attach the post that fulfilled this deal. The sponsor sees that post’s reach and
            engagement — nothing else from your account.
          </p>
          <div className="mt-3">
            <DisclosureNote rules={rules} />
          </div>
          {error && (
            <div className="mt-3 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
              {error}
            </div>
          )}

          <div className="mt-4 max-h-64 overflow-y-auto pr-2">
            {!posts && <p className="meta">Loading your posts…</p>}
            {posts?.length === 0 && (
              <EmptyNote text="No posts to attach. Sync a connected platform first — Stride can only measure what it can see." />
            )}
            {posts?.map((p) => {
              const on = attached.includes(p.post_id)
              return (
                <button
                  key={p.post_id}
                  type="button"
                  disabled={busy || on}
                  onClick={() => attach(p.post_id)}
                  className="flex w-full items-center gap-3 border-b border-line py-2.5 text-left last:border-b-0 hover:bg-raised disabled:cursor-default disabled:hover:bg-transparent"
                >
                  <span className="cap w-20 shrink-0">{platformLabel(p.platform)}</span>
                  <span className="min-w-0 flex-1 truncate text-sm text-ink">{p.title}</span>
                  <span className="w-24 shrink-0 text-right text-xs text-ink-3">{fmtDate(p.published_at)}</span>
                  <span className="tnum w-20 shrink-0 text-right text-sm text-ink-2">{fmtNum(p.reach)}</span>
                  <span className={`cap w-16 shrink-0 text-right ${on ? 'text-ok' : 'text-accent-ink'}`}>
                    {on ? 'attached' : 'attach'}
                  </span>
                </button>
              )
            })}
          </div>

          <div className="mt-5 flex items-center gap-2">
            <button className="btn-go" disabled={!attached.length || busy} onClick={() => complete(close)}>
              Mark delivered
            </button>
            <button className="btn" onClick={close}>Cancel</button>
            <span className="meta ml-auto">
              {attached.length ? `${attached.length} attached` : 'attach at least one post to deliver'}
            </span>
          </div>
        </>
      )}
    </Modal>
  )
}
