/** The review queue — the only manual step in admission.
 *
 *  Worth knowing before reading the layout: under the modelled applicant mix,
 *  **every case in this queue is waiting for a link to be opened**, not for a
 *  judgement about the athlete. A queued proof caps credibility at 0.70x, which
 *  holds a genuine regional competitor below the admit line until somebody
 *  looks. So this view is built around one action — open the link, say whether
 *  the name is on it — and everything else is context for that action.
 *
 *  It is also the argument for automating the step: see
 *  business-plan/11-admission-and-matching.md.
 */

import { Ban, Check, ExternalLink, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyNote, LoadError, Modal, PageHeader, PageLoading, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate } from '../../lib/format'
import { useToast } from '../../lib/toast'
import { openable } from '../../lib/url'
import type { AdmissionVerdict, AthleteApplication, ClubApplication, ClubLegitimacy } from '../../types'
import { DECISION_COPY, proofStatusLabel } from '../../types'

type QueueName = 'athletes' | 'clubs' | 'verified'

interface OutboxEntry {
  id: number; to: string; subject: string; body: string
  kind: string; at: string; sent: boolean
}

/** Both endpoints cap at 500. Ask for the maximum and say so when the list comes
 *  back full: the default of 100 silently hid the revoke control for every club
 *  past the hundredth, and a truncated queue looks exactly like a finished one. */
const QUEUE_LIMIT = 500

/** What a section says about itself when it is not a full, healthy list.
 *  "there may be more" rather than "there are more": a list of exactly the
 *  limit is indistinguishable from a truncated one without a count from the
 *  server, and claiming certainty either way would be made up. */
function QueueNote({ failure, shown, otherwise = '' }:
                   { failure?: string; shown: number; otherwise?: string }) {
  if (failure) return <span className="meta text-critical">could not be loaded</span>
  if (shown >= QUEUE_LIMIT) {
    return <span className="meta">showing the first {QUEUE_LIMIT} — there may be more</span>
  }
  return otherwise ? <span className="meta">{otherwise}</span> : null
}

/** Said in place of the empty state, because "nothing waiting" is the one thing
 *  a reviewer must not be told when the truth is that nobody asked. */
function QueueFailed({ what, why }: { what: string; why: string }) {
  return (
    <div className="rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
      Could not load {what}: {why}. The other queues on this page are unaffected.
    </div>
  )
}

export default function ReviewQueue() {
  const [athletes, setAthletes] = useState<AthleteApplication[]>([])
  const [clubs, setClubs] = useState<ClubApplication[]>([])
  const [verifiedClubs, setVerifiedClubs] = useState<ClubApplication[]>([])
  const [loaded, setLoaded] = useState(false)
  const [rejecting, setRejecting] = useState<AthleteApplication | null>(null)
  const [rejectingClub, setRejectingClub] = useState<ClubApplication | null>(null)
  const [clubReasons, setClubReasons] = useState<{ value: string; label: string }[]>([])
  const [reasons, setReasons] = useState<{ value: string; label: string }[]>([])
  const [outbox, setOutbox] = useState<OutboxEntry[]>([])
  const [failed, setFailed] = useState<Partial<Record<QueueName, string>>>({})
  // Two different failures, deliberately not one state. `error` is a banner
  // over a page that still works — a decision that did not post. `loadError` is
  // the page having nothing to show at all. Collapsing them meant a failed
  // decision blanked the whole queue, which is worse than what it replaced.
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [revoking, setRevoking] = useState<ClubApplication | null>(null)
  const toast = useToast()

  const load = async () => {
    // Verified clubs are fetched alongside the queue on purpose. Revocation is
    // only ever meaningful for a club that IS verified, and the first version
    // of this view listed the review queue alone — so the one control that can
    // undo a verification never rendered for any club that had one.
    //
    // `allSettled`, not `all`: these are three independent queues, and under
    // `all` a single failing request rejected the whole load, so one broken
    // query emptied the other two lists as well. A reviewer cannot tell an
    // empty queue from a failed one, so that read as "nothing to review".
    const [a, waiting, verified] = await Promise.allSettled([
      api.get<AthleteApplication[]>(`/api/admin/review-queue?decision=review&limit=${QUEUE_LIMIT}`),
      api.get<ClubApplication[]>(`/api/admin/club-queue?decision=review&limit=${QUEUE_LIMIT}`),
      api.get<ClubApplication[]>(`/api/admin/club-queue?decision=verified&limit=${QUEUE_LIMIT}`),
    ])

    // A rejected queue becomes an empty list *and* a recorded failure. Leaving
    // it null was what made `allSettled` pointless: the page-level guard below
    // saw the null and rendered an error over the two queues that did load.
    const trouble: Partial<Record<QueueName, string>> = {}
    const take = <T,>(r: PromiseSettledResult<T>, name: QueueName, set: (v: T) => void) => {
      if (r.status === 'fulfilled') set(r.value)
      else trouble[name] = errorText(r.reason)
    }
    take(a, 'athletes', setAthletes)
    take(waiting, 'clubs', setClubs)
    take(verified, 'verified', setVerifiedClubs)

    setFailed(trouble)
    // Only the load's own failure is set here. The action banner is owned by the
    // handler that raises it, which also clears it when the action is retried —
    // so `load()` writing to it as well was a second writer to one piece of
    // state and nothing more. (Removing it does not make a failed decision's
    // banner survive a later successful one: the handlers clear on retry, by
    // design. It is one less place that can start disagreeing.)
    setLoadError(Object.keys(trouble).length === 3 ? Object.values(trouble)[0] : '')
    setLoaded(true)
  }

  useEffect(() => {
    load().catch((e) => {
      setLoadError(errorText(e))
      setLoaded(true)
    })
    // served rather than hard-coded here: two copies of this list drift,
    // and the one that drifts is always the one the reviewer sees
    api.get<{ value: string; label: string }[]>('/api/admin/rejection-reasons')
      .then(setReasons).catch(() => setReasons([]))
    api.get<{ value: string; label: string }[]>('/api/admin/club-rejection-reasons')
      .then(setClubReasons).catch(() => setClubReasons([]))
    void loadOutbox()
  }, [])

  const loadOutbox = () =>
    api.get<OutboxEntry[]>('/api/admin/outbox').then(setOutbox).catch(() => setOutbox([]))

  const decideAthlete = async (application: AthleteApplication, proof_status: string,
                               reason = '', note = '') => {
    setError('')
    setBusy(application.id)
    try {
      const verdict = await api.post<AdmissionVerdict>(
        `/api/admin/applications/${application.id}/proof`, { proof_status, reason, note })
      toast(`${application.display_name}: ${DECISION_COPY[verdict.rule] ?? verdict.decision}`)
      await load()
      await loadOutbox()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(null)
    }
  }

  const decideClub = async (application: ClubApplication, proof_status: string,
                            reason = '', note = '') => {
    setError('')
    setBusy(application.id)
    try {
      const scored = await api.post<ClubLegitimacy>(
        `/api/admin/clubs/${application.club_id}/proof`, { proof_status, reason, note })
      toast(`${application.name}: ${scored.decision}`)
      await load()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(null)
    }
  }

  const revoke = async (application: ClubApplication) => {
    setError('')
    try {
      const res = await api.post<{ athletes_returned_to_review: number }>(
        `/api/admin/clubs/${application.club_id}/revoke`)
      toast(`${application.name} de-verified — ${res.athletes_returned_to_review} athlete(s) back to review`)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  // Only a total failure is a page-level error now. One queue down is a note on
  // that queue, with the other two still usable.
  if (!loaded) return <PageLoading />
  if (loadError) return <LoadError text={loadError} />

  // Only a supplied link can be checked — the server refuses `verified`
  // without one, so the control says so rather than returning an error.
  // `openable` is imported rather than defined here: it has to stay the same
  // rule as the server's, and a copy is how two rules become one bug.

  const rejectionForm = rejecting && (
    <RejectionForm
      subject={rejecting.display_name ?? 'this applicant'}
      reasons={reasons}
      busy={busy === rejecting.id}
      onClose={() => setRejecting(null)}
      onSubmit={async (reason, note) => {
        await decideAthlete(rejecting, 'rejected', reason, note)
        setRejecting(null)
      }}
    />
  )

  const clubRejectionForm = rejectingClub && (
    <RejectionForm
      subject={rejectingClub.name ?? rejectingClub.legal_name}
      reasons={clubReasons}
      busy={busy === rejectingClub.id}
      onClose={() => setRejectingClub(null)}
      onSubmit={async (reason, note) => {
        await decideClub(rejectingClub, 'rejected', reason, note)
        setRejectingClub(null)
      }}
    />
  )

  return (
    <div>
      {rejectionForm}
      {clubRejectionForm}
      <PageHeader
        eyebrow="Operations"
        title="Review queue"
        lede="Open the link, decide whether it names the applicant. Almost nothing here is a judgement call — which is the argument for eventually doing it with a crawler."
        aside={
          <span className="meta">
            {athletes.length + clubs.length} waiting
            {(failed.athletes || failed.clubs) && ' (count incomplete — a queue failed to load)'}
          </span>
        }
      />
      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      <Section title={`Athletes (${athletes.length})`}
               aside={<QueueNote failure={failed.athletes} shown={athletes.length} />}>
        {failed.athletes ? (
          <QueueFailed what="athlete applications" why={failed.athletes} />
        ) : athletes.length === 0 ? (
          <EmptyNote text="Nothing waiting. Applications arrive here when a claim clears the review floor but the evidence has not been checked." />
        ) : (
          <div className="space-y-3">
            {athletes.map((a) => (
              <div key={a.id} className="panel p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <Link to={`/athletes/${a.slug}`} className="font-medium text-ink hover:text-accent">
                    {a.display_name}
                  </Link>
                  <span className="tag">{a.sport}</span>
                  <span className="text-sm text-ink-2">
                    {a.competition_level || 'no level given'}
                    {a.league_name && ` · ${a.league_name}`}
                    {a.club_name && ` · ${a.club_name}`}
                  </span>
                  <span className="tnum ml-auto font-display text-[19px] font-bold text-ink">
                    {a.credibility?.toFixed(1) ?? '—'}
                  </span>
                  <StatusChip status={a.decision} />
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1">
                  <span className="meta">
                    {a.years_competing ?? '—'} seasons · born {a.birth_year ?? 'not given'} ·
                    submitted {fmtDate(a.submitted_at)}
                  </span>
                  <span className="meta">proof {proofStatusLabel(a.proof_status)}</span>
                  {a.nominated_by_club && <span className="tag">club-nominated</span>}
                </div>

                {/* Rendered as a link only for http(s). The URL is a string an
                    applicant typed, and an anchor will happily launch whatever
                    scheme it is given; a reviewer clicking through the queue
                    should not be the one to find that out. */}
                {openable(a.proof_url) ? (
                  <a
                    href={a.proof_url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="mt-3 inline-flex items-center gap-1.5 break-all text-sm text-accent-ink hover:text-accent"
                  >
                    <ExternalLink size={13} />
                    {a.proof_url}
                  </a>
                ) : a.proof_url ? (
                  <p className="meta mt-3 break-all">
                    Not an http(s) link, so it is shown rather than linked: {a.proof_url}
                  </p>
                ) : (
                  <p className="meta mt-3">No link supplied — nothing to open.</p>
                )}

                <div className="mt-4 flex flex-wrap gap-2">
                  <button className="btn-go" disabled={busy === a.id || !openable(a.proof_url)}
                          title={openable(a.proof_url) ? undefined : 'No link to open'}
                          onClick={() => decideAthlete(a, 'verified')}>
                    <Check size={14} /> Name is on the page
                  </button>
                  <button className="btn" disabled={busy === a.id}
                          onClick={() => setRejecting(a)}>
                    <X size={14} /> It is not
                  </button>
                  <span className="meta ml-auto self-center">
                    Rejecting sticks: only a reviewer can clear it, so re-submitting the form
                    will not wash it off.
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section title={`Clubs (${clubs.length})`}
               aside={<QueueNote failure={failed.clubs} shown={clubs.length} />}>
        {failed.clubs ? (
          <QueueFailed what="clubs awaiting verification" why={failed.clubs} />
        ) : clubs.length === 0 ? (
          <EmptyNote text="No clubs waiting on verification." />
        ) : (
          <div className="space-y-3">
            {clubs.map((c) => (
              <div key={c.id} className="panel p-5">
                <div className="flex flex-wrap items-center gap-3">
                  <Link to={`/clubs/${c.slug}`} className="font-medium text-ink hover:text-accent">
                    {c.name}
                  </Link>
                  <span className="tag">{c.sport}</span>
                  <span className="text-sm text-ink-2">
                    {c.legal_name || 'no legal name'} · {c.registration_id || 'no registration'}
                  </span>
                  <span className="tnum ml-auto font-display text-[19px] font-bold text-ink">
                    {c.legitimacy?.toFixed(1) ?? '—'}
                  </span>
                  <StatusChip status={c.decision} />
                </div>

                <div className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1">
                  <span className="meta">
                    {c.federation_name || 'no federation'}
                    {c.federation_id && ` #${c.federation_id}`} · founded{' '}
                    {c.founded_year ?? 'not given'} · {c.teams_count ?? '—'} teams ·{' '}
                    {c.registered_athletes} declared athletes
                  </span>
                  <span className="meta">roster {proofStatusLabel(c.proof_status)}</span>
                </div>

                {openable(c.roster_url) ? (
                  <a href={c.roster_url} target="_blank" rel="noreferrer noopener"
                     className="mt-3 inline-flex items-center gap-1.5 break-all text-sm text-accent-ink hover:text-accent">
                    <ExternalLink size={13} />
                    {c.roster_url}
                  </a>
                ) : c.roster_url ? (
                  <p className="meta mt-3 break-all">
                    Not an http(s) link, so it is shown rather than linked: {c.roster_url}
                  </p>
                ) : (
                  <p className="meta mt-3">No roster page supplied — nothing to open.</p>
                )}

                <div className="mt-4 flex flex-wrap gap-2">
                  <button className="btn-go" disabled={busy === c.id || !openable(c.roster_url)}
                          title={openable(c.roster_url) ? undefined : 'No roster page to open'}
                          onClick={() => decideClub(c, 'verified')}>
                    <Check size={14} /> Roster checks out
                  </button>
                  <button className="btn" disabled={busy === c.id}
                          onClick={() => setRejectingClub(c)}>
                    <X size={14} /> It does not
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      <Section
        title={`Verified clubs (${verifiedClubs.length})`}
        aside={
          <QueueNote failure={failed.verified} shown={verifiedClubs.length}
                     otherwise="each can nominate; each can be withdrawn" />
        }
      >
        {failed.verified ? (
          <QueueFailed what="verified clubs" why={failed.verified} />
        ) : verifiedClubs.length === 0 ? (
          <EmptyNote text="No verified clubs yet. A club appears here once its roster page has been checked." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Club</th>
                <th className="table-head">Federation</th>
                <th className="table-head text-right">Legitimacy</th>
                <th className="table-head text-right">Nomination floor</th>
                <th className="table-head" />
              </tr>
            </thead>
            <tbody>
              {verifiedClubs.map((c) => (
                <tr key={c.id}>
                  <td className="table-cell">
                    <Link to={`/clubs/${c.slug}`} className="text-ink hover:text-accent">{c.name}</Link>
                    <span className="ml-2 text-xs text-ink-3">{c.sport}</span>
                  </td>
                  <td className="table-cell text-ink-3">
                    {c.federation_name || '—'}{c.federation_id && ` #${c.federation_id}`}
                  </td>
                  <td className="table-cell tnum text-right">{c.legitimacy?.toFixed(1) ?? '—'}</td>
                  <td className="table-cell tnum text-right">
                    {c.scored?.nomination_floor.toFixed(1) ?? '—'}
                  </td>
                  <td className="table-cell text-right">
                    <button className="btn px-2.5 py-1 text-xs" onClick={() => setRevoking(c)}>
                      <Ban size={13} /> Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {revoking && (
        <Modal title={`Revoke — ${revoking.name}`} onClose={() => setRevoking(null)}>
          {(close) => (
            <div>
              <p className="text-sm text-ink-2">
                This de-verifies the club and withdraws what its nominations were holding up.
                Athletes whose own credibility already cleared the admit line keep their
                place; the rest go back to review and are delisted until then.
              </p>
              <p className="meta mt-2">
                Review, not rejection — losing your supporting evidence is not the same as
                being caught lying.
              </p>
              <div className="mt-5 flex gap-2">
                <button
                  className="btn-go"
                  onClick={async () => {
                    close()
                    await revoke(revoking)
                    setRevoking(null)
                  }}
                >
                  Revoke verification
                </button>
                <button className="btn" onClick={close}>Cancel</button>
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* What the product owes people. Nothing is sent — there is no mail
          provider — so showing the queue is the honest version of "an email
          was sent": the reviewer reads the exact text the applicant gets. */}
      <Section title="Outbox"
               aside={<span className="meta">{outbox.length} queued · nothing is delivered in the demo</span>}>
        {outbox.length === 0 ? (
          <EmptyNote text="No messages owed. Deciding an application writes one here." />
        ) : (
          <div className="space-y-2">
            {outbox.map((e) => (
              <details key={e.id} className="panel p-4">
                <summary className="cursor-pointer list-none">
                  <span className="font-medium text-ink">{e.subject}</span>
                  <span className="meta ml-2">to {e.to}</span>
                  <span className={`tag ml-2 ${e.sent ? 'text-ok' : ''}`}>
                    {e.sent ? 'sent' : 'queued'}
                  </span>
                </summary>
                <pre className="mt-3 whitespace-pre-wrap font-sans text-sm text-ink-2">{e.body}</pre>
              </details>
            ))}
          </div>
        )}
      </Section>

    </div>
  )
}


/** Refusing needs a reason, and the applicant is told what it was.
 *
 *  A one-click reject was faster for the reviewer and useless to everyone
 *  after: the athlete learns only that they failed, and the next reviewer to
 *  see the case inherits no record of what was already checked. The reason is
 *  a fixed list so the outcomes can be counted; the note is free text because
 *  the interesting cases never fit a list.
 */
function RejectionForm({ subject, reasons, busy, onClose, onSubmit }: {
  subject: string
  reasons: { value: string; label: string }[]
  busy: boolean
  onClose: () => void
  onSubmit: (reason: string, note: string) => void
}) {
  const [reason, setReason] = useState(reasons[0]?.value ?? 'name_not_on_page')
  const [note, setNote] = useState('')
  // "other" is the escape hatch, so it cannot also be a way to say nothing
  const needsNote = reason === 'other' && !note.trim()

  return (
    <Modal title={`Reject ${subject}?`} onClose={onClose}>
      {(close) => (
        <div className="space-y-4">
          <p className="text-sm text-ink-2">
            They are told the reason, in these words, and can submit a different link.
          </p>

          <label className="block"><span className="cap">Reason *</span>
            <select className="field mt-1" value={reason} onChange={(e) => setReason(e.target.value)}>
              {reasons.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </label>

          <label className="block"><span className="cap">Note to the applicant</span>
            <textarea className="field mt-1 min-h-[6rem]" value={note}
                      placeholder="Anything they should know. Sent as written."
                      onChange={(e) => setNote(e.target.value)} />
            {reason === 'other' && (
              <span className="meta mt-1 block">Required when the reason is “something else”.</span>
            )}
          </label>

          <div className="flex items-center gap-3">
            <button className="btn-go" disabled={busy || needsNote}
                    onClick={() => { onSubmit(reason, note.trim()); close() }}>
              {busy ? 'Recording…' : 'Reject and tell them'}
            </button>
            <button className="btn" onClick={close}>Cancel</button>
            <span className="meta">Rejecting sticks — only a reviewer can clear it.</span>
          </div>
        </div>
      )}
    </Modal>
  )
}
