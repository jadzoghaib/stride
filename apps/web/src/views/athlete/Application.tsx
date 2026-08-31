/** The athlete's side of the admission gate.
 *
 *  Its whole job is that the applicant can see what was decided and what would
 *  change it. The server returns the components, the weights, the evidence
 *  multiplier and a machine-readable rule for exactly this reason — a gate whose
 *  result cannot be explained to the person it excluded is a gate they cannot
 *  appeal, and that is the one thing this product has consistently refused to
 *  ship.
 */

import { useEffect, useState } from 'react'
import { Board } from '../../components/Board'
import { FormRow, ReasonLists, ScoreBreakdown, ThresholdRule, VerdictNote } from '../../components/Admission'
import { LoadError, PageHeader, PageLoading, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { openable } from '../../lib/url'
import { fmtDate } from '../../lib/format'
import { useToast } from '../../lib/toast'
import type { AdmissionVerdict, AthleteApplicationView } from '../../types'
import { COMPETITION_LEVELS, DECISION_COPY, PROOF_KINDS, proofStatusLabel } from '../../types'

const LEVEL_HELP: Record<string, string> = {
  local: 'Club or town level competition.',
  regional: 'Provincial, county or state competition.',
  national: 'National championship or national league.',
  international: 'Representing your country, or an international circuit.',
}

interface FormState {
  competition_level: string
  discipline: string
  club_name: string
  league_name: string
  years_competing: string
  birth_year: string
  proof_kind: string
  proof_url: string
}

const EMPTY: FormState = {
  competition_level: '', discipline: '', club_name: '', league_name: '',
  years_competing: '', birth_year: '', proof_kind: 'none', proof_url: '',
}

export default function AthleteApplication() {
  const [view, setView] = useState<AthleteApplicationView | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const toast = useToast()

  const load = () =>
    api.get<AthleteApplicationView>('/api/athlete/application').then((v) => {
      setView(v)
      if (v.application) {
        setForm({
          competition_level: v.application.competition_level,
          discipline: v.application.discipline,
          club_name: v.application.club_name,
          league_name: v.application.league_name,
          years_competing: v.application.years_competing?.toString() ?? '',
          birth_year: v.application.birth_year?.toString() ?? '',
          proof_kind: v.application.proof_kind,
          proof_url: v.application.proof_url,
        })
      }
    })

  useEffect(() => {
    load().catch((e) => setError(errorText(e)))
  }, [])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const verdict = await api.post<AdmissionVerdict>('/api/athlete/application', {
        competition_level: form.competition_level,
        discipline: form.discipline,
        club_name: form.club_name,
        league_name: form.league_name,
        years_competing: form.years_competing === '' ? null : Number(form.years_competing),
        birth_year: form.birth_year === '' ? null : Number(form.birth_year),
        proof_kind: form.proof_kind,
        proof_url: form.proof_url,
      })
      // The verdict alone left the most consequential part unsaid: whether the
      // profile is still in the directory. Someone who submits a form and
      // silently drops out of matching has been told nothing that matters.
      // "while this is checked" was only true for a review. The backend returns
      // draft for a rejection, for a claim weakened after admission, and for an
      // admitted athlete with no analytics yet — telling all of them to sit
      // tight would be the same silence in a friendlier font.
      const outcome = DECISION_COPY[verdict.rule] ?? `Submitted — ${verdict.decision}`
      toast(verdict.listing === 'listed'
        ? `${outcome} Your profile stays in the directory.`
        : `${outcome} Your profile is not in the directory — see the decision below for why.`)
      await load()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  if (!view) return error ? <LoadError text={error} /> : <PageLoading />

  const { application, scored } = view
  const set = (k: keyof FormState) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  return (
    <>
      {view?.frozen && <Frozen frozen={view.frozen} onRedeemed={load} />}

      {application && scored ? (
        <Board
          eyebrow="Athlete"
          title="Eligibility"
          tags={<StatusChip status={application.decision} />}
          score={scored.credibility}
          scoreLabel="Credibility"
          scoreFormat={(n) => n.toFixed(1)}
          rulePct={scored.credibility}
          deltaNote={DECISION_COPY[application.decision_rule] ?? application.decision}
          trendEmpty="Credibility is what admits you. Your analytics decide how prominently you are listed."
          figures={[
            { label: 'Evidence', value: `×${scored.evidence_multiplier.toFixed(2)}` },
            { label: 'Proof', value: proofStatusLabel(application.proof_status) },
            { label: 'Admit at', value: view.thresholds?.admit ?? 55 },
            ...(view.club_floor
              ? [{ label: 'Club floor', value: view.club_floor.toFixed(1) }]
              : []),
          ]}
          footNote={application.decided_at ? `decided ${fmtDate(application.decided_at)}` : undefined}
        />
      ) : (
        <PageHeader
          eyebrow="Athlete"
          title="Eligibility"
          lede="Stride is for people who actually compete. Tell us where you compete and give us something we can check — that is the whole gate."
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
              <VerdictNote
                decision={application.decision}
                copy={DECISION_COPY[application.decision_rule] ?? application.decision}
              />
              <div className="mt-4 max-w-lg">
                <ThresholdRule
                  value={Math.max(scored.credibility, view.club_floor ?? 0)}
                  admit={view.thresholds?.admit ?? 55}
                  review={25}
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
                total={scored.credibility}
                totalLabel="Credibility"
                proofStatus={application.proof_status}
              />
            </Section>
          </>
        )}

        <Section title={application ? 'Update your application' : 'Apply'}>
          <form onSubmit={submit} className="panel space-y-4 p-5">
            <div className="grid gap-4 md:grid-cols-2">
              <FormRow
                label="Competition level *"
                hint={LEVEL_HELP[form.competition_level] ?? 'Required — nothing can be assessed without it.'}
              >
                <select className="field mt-1" value={form.competition_level} onChange={set('competition_level')}>
                  <option value="">Select a level</option>
                  {COMPETITION_LEVELS.map((l) => (
                    <option key={l} value={l}>{l}</option>
                  ))}
                </select>
              </FormRow>
              <FormRow label="Discipline or position" hint="e.g. 800m, left back, singles">
                <input className="field mt-1" value={form.discipline} onChange={set('discipline')} />
              </FormRow>
              <FormRow label="Club">
                <input className="field mt-1" value={form.club_name} onChange={set('club_name')} />
              </FormRow>
              <FormRow label="League or competition">
                <input className="field mt-1" value={form.league_name} onChange={set('league_name')} />
              </FormRow>
              <FormRow
                label="Seasons competing"
                hint="Eight or more is full marks. Blank scores zero — it is never left out."
              >
                <input className="field mt-1 tnum" type="number" min={0} max={60}
                       value={form.years_competing} onChange={set('years_competing')} />
              </FormRow>
              <FormRow
                label="Year of birth"
                hint="Accounts are 16 and over, and we cannot admit anyone whose age we do not know."
              >
                <input className="field mt-1 tnum" type="number" min={1930} max={2030}
                       value={form.birth_year} onChange={set('birth_year')} />
              </FormRow>
            </div>

            <div className="rounded-card border border-line bg-raised p-4">
              <div className="cap mb-3">Proof of participation</div>
              <p className="mb-3 text-sm text-ink-2">
                A page a stranger can open and find your name on. This is the single biggest
                thing in the score: an unchecked claim is worth a fraction of a checked one,
                whatever the claim says.
              </p>
              <div className="grid gap-4 md:grid-cols-2">
                <FormRow label="Kind">
                  <select className="field mt-1" value={form.proof_kind} onChange={set('proof_kind')}>
                    {PROOF_KINDS.map((k) => (
                      <option key={k} value={k}>
                        {k === 'none' ? 'none yet' : k}
                      </option>
                    ))}
                  </select>
                </FormRow>
                <FormRow label="Link" hint="Club roster, federation licence, or official results.">
                  <input className="field mt-1" placeholder="https://" value={form.proof_url}
                         onChange={set('proof_url')} />
                </FormRow>
              </div>
              {/* Naming a kind of proof and leaving the box empty scores exactly
                  the same as claiming none — there is nothing for a reviewer to
                  open. Better said here than discovered in the verdict. */}
              {form.proof_kind !== 'none' && !openable(form.proof_url) && (
                <p className="meta mt-3 text-ink-2">
                  {form.proof_url.trim()
                    ? `“${form.proof_url.trim()}” is not a page anyone can open, so it counts as no proof.`
                    : `A ${form.proof_kind} with no link counts as no proof: nobody can check it.`}{' '}
                  Add a full https:// address, or set the kind to “none yet”.
                </p>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-go" disabled={busy}>
                {application ? 'Resubmit' : 'Submit application'}
              </button>
              {application?.proof_status === 'verified' && (
                <span className="meta">
                  Resubmitting sends your proof back to be checked — the link was checked
                  against the claim you are about to change.
                </span>
              )}
            </div>
          </form>
        </Section>
      </div>
    </>
  )
}


/** What a frozen athlete is told, and the two doors out of it.
 *
 *  Freezing happens when the club that vouched for someone withdraws it, which
 *  removes the only evidence their listing stood on. Saying just "you are not
 *  listed" would be true and useless: the page has to name who withdrew it and
 *  both routes back, because neither is discoverable otherwise.
 */
function Frozen({ frozen, onRedeemed }: {
  frozen: { at: string; club: string | null }
  onRedeemed: () => void
}) {
  const [token, setToken] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const redeem = async () => {
    setBusy(true)
    setError('')
    try {
      await api.post(`/api/athlete/invite-links/${token.trim()}/redeem`, {})
      setToken('')
      onRedeemed()
    } catch (e) { setError(errorText(e)) } finally { setBusy(false) }
  }

  return (
    <div className="mb-6 rounded-card border border-critical/45 bg-critical/10 p-5">
      <p className="cap text-critical">Profile frozen</p>
      <p className="mt-2 text-sm text-ink-2">
        {frozen.club ?? 'The club that vouched for you'} withdrew their invitation, so your
        profile is out of the directory. Your account and everything you have published are
        untouched.
      </p>
      <p className="mt-3 text-sm text-ink-2">There are two ways back:</p>
      <ol className="mt-1 list-inside list-decimal space-y-1 text-sm text-ink-2">
        <li>Redeem a new invite link from a verified club.</li>
        <li>Submit a proof link of your own below and have it checked.</li>
      </ol>

      <div className="mt-4 flex flex-wrap items-end gap-2">
        <label className="block"><span className="cap">Invite link or code</span>
          <input className="field mt-1 w-72" value={token} placeholder="Paste the code"
                 onChange={(e) => setToken(e.target.value.trim().split('invite=').pop() ?? '')} />
        </label>
        <button className="btn-go" disabled={busy || !token.trim()} onClick={redeem}>
          {busy ? 'Checking…' : 'Redeem'}
        </button>
      </div>
      {error && <p className="mt-2 text-sm text-critical">{error}</p>}
    </div>
  )
}
