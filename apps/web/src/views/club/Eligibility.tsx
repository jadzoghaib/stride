/** The club's side of the gate, and what its word is worth.
 *
 *  Two things this view has to be honest about, because both are counter-
 *  intuitive and both are load-bearing:
 *
 *  - Verification is about being *real*, not about being *big*. Nothing here
 *    scores a following; reach belongs in package pricing.
 *  - A nomination is a floor, not a bypass. It raises an athlete's credibility
 *    and cannot finish the job, because no club can supply someone else's date
 *    of birth. Saying so plainly avoids a club nominating twenty people and
 *    wondering why none of them are listed.
 */

import { BadgeCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Board } from '../../components/Board'
import { FormRow, ReasonLists, ScoreBreakdown, ThresholdRule, VerdictNote } from '../../components/Admission'
import { EmptyNote, LoadError, PageHeader, PageLoading, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate } from '../../lib/format'
import { useToast } from '../../lib/toast'
import type { AdmissionVerdict, ClubApplicationView, ClubLegitimacy, ClubWorkspace } from '../../types'
import { COMPETITION_LEVELS, DECISION_COPY, PROOF_KINDS, proofStatusLabel } from '../../types'

const CLUB_COPY: Record<string, string> = {
  verified: 'Verified. Your nominations now carry a credibility floor to the athletes you name.',
  review: 'With our team. Nothing is wrong — someone has to open your roster page before this can be verified.',
  rejected: 'Not enough that we can check. Add a registration number, a federation affiliation and a public roster.',
  pending: 'Not submitted yet.',
}

interface FormState {
  legal_name: string
  registration_id: string
  federation_name: string
  federation_id: string
  founded_year: string
  competition_level: string
  teams_count: string
  registered_athletes: string
  roster_url: string
  proof_kind: string
}

const EMPTY: FormState = {
  legal_name: '', registration_id: '', federation_name: '', federation_id: '',
  founded_year: '', competition_level: '', teams_count: '', registered_athletes: '',
  roster_url: '', proof_kind: 'none',
}

export default function ClubEligibility() {
  const [view, setView] = useState<ClubApplicationView | null>(null)
  const [ws, setWs] = useState<ClubWorkspace | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [outcomes, setOutcomes] = useState<Record<string, string>>({})
  const toast = useToast()

  const load = async () => {
    const [v, w] = await Promise.all([
      api.get<ClubApplicationView>('/api/club/application'),
      api.get<ClubWorkspace>('/api/club/workspace'),
    ])
    setView(v)
    setWs(w)
    if (v.application) {
      const a = v.application
      setForm({
        legal_name: a.legal_name, registration_id: a.registration_id,
        federation_name: a.federation_name, federation_id: a.federation_id,
        founded_year: a.founded_year?.toString() ?? '',
        competition_level: a.competition_level,
        teams_count: a.teams_count?.toString() ?? '',
        registered_athletes: a.registered_athletes.toString(),
        roster_url: a.roster_url, proof_kind: a.proof_kind,
      })
    }
  }

  useEffect(() => {
    load().catch((e) => setError(errorText(e)))
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const scored = await api.post<ClubLegitimacy>('/api/club/application', {
        legal_name: form.legal_name,
        registration_id: form.registration_id,
        federation_name: form.federation_name,
        federation_id: form.federation_id,
        founded_year: form.founded_year === '' ? null : Number(form.founded_year),
        competition_level: form.competition_level,
        teams_count: form.teams_count === '' ? null : Number(form.teams_count),
        registered_athletes: form.registered_athletes === '' ? 0 : Number(form.registered_athletes),
        roster_url: form.roster_url,
        proof_kind: form.proof_kind,
      })
      toast(CLUB_COPY[scored.decision] ?? `Submitted — ${scored.decision}`)
      await load()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  const nominate = async (slug: string) => {
    setError('')
    try {
      const verdict = await api.post<AdmissionVerdict>('/api/club/nominations', { athlete_slug: slug })
      setOutcomes((o) => ({ ...o, [slug]: DECISION_COPY[verdict.rule] ?? verdict.decision }))
      toast(`Nominated — ${verdict.decision}`)
      await load()
    } catch (err) {
      setOutcomes((o) => ({ ...o, [slug]: errorText(err) }))
    }
  }

  if (!view || !ws) return error ? <LoadError text={error} /> : <PageLoading />

  const { application, scored, nominations } = view
  const set = (k: keyof FormState) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))
  const budgetLeft = (nominations?.budget ?? 0) - (nominations?.used ?? 0)

  return (
    <>
      {application && scored ? (
        <Board
          eyebrow="Club"
          title="Eligibility"
          tags={<StatusChip status={application.decision} />}
          score={scored.legitimacy}
          scoreLabel="Legitimacy"
          scoreFormat={(n) => n.toFixed(1)}
          rulePct={scored.legitimacy}
          deltaNote={CLUB_COPY[application.decision] ?? application.decision}
          trendEmpty="Scored on what makes a club real, not on what makes it marketable."
          figures={[
            { label: 'Evidence', value: `×${scored.evidence_multiplier.toFixed(2)}` },
            { label: 'Roster page', value: proofStatusLabel(application.proof_status) },
            { label: 'Nomination floor', value: scored.nomination_floor.toFixed(1) },
            { label: 'Nominations', value: `${nominations?.used ?? 0} / ${nominations?.budget ?? 0}` },
          ]}
          footNote={application.decided_at ? `decided ${fmtDate(application.decided_at)}` : undefined}
        />
      ) : (
        <PageHeader
          eyebrow="Club"
          title="Eligibility"
          lede="A verified club can vouch for the athletes on its roster. What we score is whether the club is real — registration, affiliation, history, teams, a public roster."
        />
      )}

      <div>
        {error && (
          <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
            {error}
          </div>
        )}

        {application && scored && (
          <>
            <Section title="Where you stand">
              <VerdictNote decision={application.decision} copy={CLUB_COPY[application.decision] ?? ''} />
              <div className="mt-4 max-w-lg">
                <ThresholdRule
                  value={scored.legitimacy}
                  admit={scored.thresholds.verify}
                  review={scored.thresholds.review}
                  admitLabel="verified"
                />
              </div>
              <div className="mt-5">
                <ReasonLists reasons={scored.reasons} caveats={scored.caveats} />
              </div>
            </Section>

            <Section
              title="How that number was reached"
              aside={<span className="meta">policy {scored.policy_version}</span>}
            >
              <ScoreBreakdown
                components={scored.components}
                weights={scored.weights}
                missing={scored.missing}
                claim={scored.claim}
                multiplier={scored.evidence_multiplier}
                total={scored.legitimacy}
                totalLabel="Legitimacy"
                proofStatus={application.proof_status}
              />
            </Section>
          </>
        )}

        <Section
          title={`Nominate from your roster (${nominations?.used ?? 0} of ${nominations?.budget ?? 0} used)`}
          aside={
            application?.decision === 'verified' ? (
              <span className="meta">{budgetLeft} left</span>
            ) : (
              <span className="meta">available once verified</span>
            )
          }
        >
          <div className="rounded-card border border-line bg-raised px-4 py-3">
            <p className="text-sm text-ink-2">
              A nomination raises an athlete&rsquo;s credibility — it does not admit them. It
              cannot: we still need their date of birth and their competition level, and no
              club can give us those on someone else&rsquo;s behalf. Expect your nominees to
              sit at <span className="text-ink">pending</span> until they finish their own
              form.
            </p>
            <p className="meta mt-1.5">
              Your budget is the roster size you declared. Raise it in the application below
              if you have more athletes than places.
            </p>
          </div>

          {ws.roster.length === 0 ? (
            <div className="mt-3">
              <EmptyNote text="No roster yet — add athletes in Club HQ, then nominate them here." />
            </div>
          ) : (
            <table className="mt-3 w-full text-sm">
              <thead>
                <tr>
                  <th className="table-head">Athlete</th>
                  <th className="table-head">Position</th>
                  <th className="table-head">Result</th>
                  <th className="table-head" />
                </tr>
              </thead>
              <tbody>
                {ws.roster.map((m) => (
                  <tr key={m.membership_id}>
                    <td className="table-cell">
                      <Link to={`/athletes/${m.slug}`} className="text-ink hover:text-accent">
                        {m.display_name}
                      </Link>
                      <span className="ml-2 text-xs text-ink-3">{m.sport}</span>
                    </td>
                    <td className="table-cell text-ink-3">{m.position || '—'}</td>
                    <td className="table-cell text-xs text-ink-2">{outcomes[m.slug] ?? '—'}</td>
                    <td className="table-cell text-right">
                      <button
                        className="btn px-2.5 py-1 text-xs"
                        disabled={application?.decision !== 'verified' || budgetLeft <= 0}
                        onClick={() => nominate(m.slug)}
                      >
                        <BadgeCheck size={13} /> Nominate
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Section>

        <Section title={application ? 'Update your application' : 'Apply'}>
          <form onSubmit={submit} className="panel space-y-4 p-5">
            <div className="grid gap-4 md:grid-cols-2">
              <FormRow label="Registered legal name">
                <input className="field mt-1" value={form.legal_name} onChange={set('legal_name')} />
              </FormRow>
              <FormRow label="Registration number" hint="CIF/NIF or the equivalent where you are registered.">
                <input className="field mt-1" value={form.registration_id} onChange={set('registration_id')} />
              </FormRow>
              <FormRow label="Federation">
                <input className="field mt-1" value={form.federation_name} onChange={set('federation_name')} />
              </FormRow>
              <FormRow label="Affiliation number" hint="A name is a claim; a number is something we can look up.">
                <input className="field mt-1" value={form.federation_id} onChange={set('federation_id')} />
              </FormRow>
              <FormRow label="Founded">
                <input className="field mt-1 tnum" type="number" min={1800} max={2030}
                       value={form.founded_year} onChange={set('founded_year')} />
              </FormRow>
              <FormRow label="Competition level">
                <select className="field mt-1" value={form.competition_level} onChange={set('competition_level')}>
                  <option value="">Select a level</option>
                  {COMPETITION_LEVELS.map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </FormRow>
              <FormRow label="Teams fielded">
                <input className="field mt-1 tnum" type="number" min={0} max={200}
                       value={form.teams_count} onChange={set('teams_count')} />
              </FormRow>
              <FormRow
                label="Registered athletes"
                hint="Also your nomination budget — so this number is one we can check against your roster page."
              >
                <input className="field mt-1 tnum" type="number" min={0} max={5000}
                       value={form.registered_athletes} onChange={set('registered_athletes')} />
              </FormRow>
            </div>

            <div className="rounded-card border border-line bg-raised p-4">
              <div className="cap mb-3">Public roster</div>
              <p className="mb-3 text-sm text-ink-2">
                A page a stranger can open and read your teams from. Verification means
                somebody actually opened it — a perfectly filled form with nothing behind it
                does not verify a club.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <FormRow label="Kind">
                  <select className="field mt-1" value={form.proof_kind} onChange={set('proof_kind')}>
                    {PROOF_KINDS.map((k) => (
                      <option key={k} value={k}>{k === 'none' ? 'none yet' : k}</option>
                    ))}
                  </select>
                </FormRow>
                <FormRow label="Link">
                  <input className="field mt-1" placeholder="https://" value={form.roster_url}
                         onChange={set('roster_url')} />
                </FormRow>
              </div>
            </div>

            <button className="btn-go" disabled={busy}>
              {application ? 'Resubmit' : 'Submit application'}
            </button>
          </form>
        </Section>
      </div>
    </>
  )
}
