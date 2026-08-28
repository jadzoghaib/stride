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
import type { AdmissionVerdict, AthleteApplication, ClubApplication, ClubLegitimacy } from '../../types'
import { DECISION_COPY, proofStatusLabel } from '../../types'

export default function ReviewQueue() {
  const [athletes, setAthletes] = useState<AthleteApplication[] | null>(null)
  const [clubs, setClubs] = useState<ClubApplication[] | null>(null)
  const [verifiedClubs, setVerifiedClubs] = useState<ClubApplication[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [revoking, setRevoking] = useState<ClubApplication | null>(null)
  const toast = useToast()

  const load = async () => {
    // Verified clubs are fetched alongside the queue on purpose. Revocation is
    // only ever meaningful for a club that IS verified, and the first version
    // of this view listed the review queue alone — so the one control that can
    // undo a verification never rendered for any club that had one.
    const [a, waiting, verified] = await Promise.all([
      api.get<AthleteApplication[]>('/api/admin/review-queue?decision=review'),
      api.get<ClubApplication[]>('/api/admin/club-queue?decision=review'),
      api.get<ClubApplication[]>('/api/admin/club-queue?decision=verified'),
    ])
    setAthletes(a)
    setClubs(waiting)
    setVerifiedClubs(verified)
  }

  useEffect(() => {
    load().catch((e) => setError(errorText(e)))
  }, [])

  const decideAthlete = async (application: AthleteApplication, proof_status: string) => {
    setError('')
    setBusy(application.id)
    try {
      const verdict = await api.post<AdmissionVerdict>(
        `/api/admin/applications/${application.id}/proof`, { proof_status })
      toast(`${application.display_name}: ${DECISION_COPY[verdict.rule] ?? verdict.decision}`)
      await load()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(null)
    }
  }

  const decideClub = async (application: ClubApplication, proof_status: string) => {
    setError('')
    setBusy(application.id)
    try {
      const scored = await api.post<ClubLegitimacy>(
        `/api/admin/clubs/${application.club_id}/proof`, { proof_status })
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

  if (!athletes || !clubs) return error ? <LoadError text={error} /> : <PageLoading />

  /** Only a supplied link can be checked — the server refuses `verified`
   *  without one, so the control says so rather than returning an error. */
  const openable = (url: string) => /^https?:\/\//i.test((url || '').trim())

  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="Review queue"
        lede="Open the link, decide whether it names the applicant. Almost nothing here is a judgement call — which is the argument for eventually doing it with a crawler."
        aside={<span className="meta">{athletes.length + clubs.length} waiting</span>}
      />
      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      <Section title={`Athletes (${athletes.length})`}>
        {athletes.length === 0 ? (
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
                          onClick={() => decideAthlete(a, 'rejected')}>
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

      <Section title={`Clubs (${clubs.length})`}>
        {clubs.length === 0 ? (
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
                          onClick={() => decideClub(c, 'rejected')}>
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
        aside={<span className="meta">each can nominate; each can be withdrawn</span>}
      >
        {verifiedClubs.length === 0 ? (
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
    </div>
  )
}
