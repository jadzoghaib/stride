import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Wordmark } from '../components/Shell'
import { api, errorText } from '../lib/api'
import { roleHome, useAuth } from '../lib/auth'
import { COMPETITION_LEVELS, PROOF_KINDS } from '../types'
import type { Me } from '../types'

const ROLES = [
  { key: 'athlete', title: 'Athlete', body: 'Connect platforms, publish your rate card, receive and manage sponsorship offers.' },
  { key: 'club', title: 'Club', body: 'Manage a roster of athletes and publish sponsorship packages — including packages that back individual players.' },
  { key: 'sponsor', title: 'Sponsor', body: 'Build campaign briefs, match against the athlete pool, and back clubs or individual players.' },
  { key: 'fan', title: 'Supporter', body: 'Follow athletes, track their trajectory, and discover new names by interest.' },
]

const DEMO = [
  { label: 'Athlete', email: 'athlete@demo.stride' },
  { label: 'Club', email: 'club@demo.stride' },
  { label: 'Sponsor', email: 'sponsor@demo.stride' },
  { label: 'Supporter', email: 'fan@demo.stride' },
  { label: 'Admin', email: 'admin@demo.stride' },
]

export default function Auth() {
  const [params] = useSearchParams()
  const [mode, setMode] = useState<'login' | 'register'>(params.get('mode') === 'register' ? 'register' : 'login')
  const [role, setRole] = useState('athlete')
  const [form, setForm] = useState({ email: '', password: '', display_name: '', sport: '', country: '', org_name: '', industry: 'Sportswear' })
  /** Registration is two steps for the roles that have to qualify. Step one
   *  creates the account — which lands as `draft`, invisible to the directory
   *  and to matching — and step two is the eligibility check that decides
   *  whether it becomes anything more. Putting the check behind a nav tab let
   *  an athlete hold an account indefinitely without ever facing it. */
  const [step, setStep] = useState<'account' | 'eligibility'>('account')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const { refresh } = useAuth()
  const navigate = useNavigate()

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const me =
        mode === 'login'
          ? await api.post<Me & { needs_email_confirmation?: boolean }>('/api/auth/login', { email: form.email, password: form.password })
          : await api.post<Me & { needs_email_confirmation?: boolean }>('/api/auth/register', { ...form, role })
      if (me.needs_email_confirmation) {
        setNotice('Account created. Check your inbox for the confirmation email, then sign in.')
        setMode('login')
        return
      }
      await refresh()
      if (mode === 'register' && (role === 'athlete' || role === 'club')) {
        setStep('eligibility')
        return
      }
      navigate(roleHome(me.role))
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  const [gate, setGate] = useState({
    competition_level: '', discipline: '', club_name: '', league_name: '',
    years_competing: '', birth_year: '', proof_url: '', proof_kind: 'none',
    legal_name: '', registration_id: '', federation_name: '', federation_id: '',
    founded_year: '', teams_count: '', registered_athletes: '', roster_url: '',
  })
  const setGateField = (k: string, v: string) => setGate((g) => ({ ...g, [k]: v }))

  /** Step two. The account exists and is `draft`; this is what decides whether
   *  it becomes visible. Posted to the same endpoints the review queue reads,
   *  so an application made at signup and one edited later are the same object. */
  const submitGate = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      if (role === 'athlete') {
        await api.post('/api/athlete/application', {
          competition_level: gate.competition_level,
          discipline: gate.discipline,
          club_name: gate.club_name,
          league_name: gate.league_name,
          years_competing: gate.years_competing === '' ? null : Number(gate.years_competing),
          birth_year: gate.birth_year === '' ? null : Number(gate.birth_year),
          proof_url: gate.proof_url,
          proof_kind: gate.proof_kind,
        })
      } else {
        await api.post('/api/club/application', {
          legal_name: gate.legal_name,
          registration_id: gate.registration_id,
          federation_name: gate.federation_name,
          federation_id: gate.federation_id,
          founded_year: gate.founded_year === '' ? null : Number(gate.founded_year),
          competition_level: gate.competition_level,
          teams_count: gate.teams_count === '' ? null : Number(gate.teams_count),
          registered_athletes: gate.registered_athletes === '' ? 0 : Number(gate.registered_athletes),
          roster_url: gate.roster_url,
          proof_kind: gate.proof_kind,
        })
      }
      navigate(roleHome(role))
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  const Field = ({ label, k, hint, type = 'text', placeholder = '' }:
                 { label: string; k: string; hint?: string; type?: string; placeholder?: string }) => (
    <label className="block">
      <span className="cap">{label}</span>
      <input className="field mt-1" type={type} placeholder={placeholder}
             value={(gate as Record<string, string>)[k]}
             onChange={(e) => setGateField(k, e.target.value)} />
      {hint && <span className="meta mt-1 block">{hint}</span>}
    </label>
  )

  if (step === 'eligibility') {
    return (
      <div className="min-h-screen bg-ground">
        <header className="mx-auto flex h-16 max-w-[1140px] items-center px-7">
          <Link to="/"><Wordmark size="text-[22px]" /></Link>
        </header>
        <div className="mx-auto max-w-2xl px-7 py-10">
          <p className="cap">Step 2 of 2</p>
          <h1 className="mt-1 font-display text-3xl font-bold text-ink">Eligibility</h1>
          <p className="mt-2 text-sm text-ink-2">
            {role === 'athlete'
              ? 'Stride is for people who actually compete. Tell us where you compete and give us something we can check — that is the whole gate.'
              : 'Tell us who the club is and give us a roster page we can open. A club has to be checked before it can vouch for anyone.'}
          </p>
          <p className="meta mt-3">
            Your account exists already. It stays out of the directory until this is reviewed.
          </p>

          {error && (
            <div className="mt-5 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
              {error}
            </div>
          )}

          <form onSubmit={submitGate} className="mt-6 space-y-4">
            <label className="block">
              <span className="cap">Competition level *</span>
              <select className="field mt-1" value={gate.competition_level}
                      onChange={(e) => setGateField('competition_level', e.target.value)}>
                <option value="">Select a level</option>
                {COMPETITION_LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
              <span className="meta mt-1 block">Required — nothing can be assessed without it.</span>
            </label>

            {role === 'athlete' ? (
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Discipline or position" k="discipline" placeholder="800m, left back, singles" />
                <Field label="Club" k="club_name" />
                <Field label="League or competition" k="league_name" />
                <Field label="Seasons competing" k="years_competing" type="number"
                       hint="Eight or more is full marks. Blank scores zero." />
                <Field label="Year of birth" k="birth_year" type="number"
                       hint="Accounts are 16 and over." />
              </div>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Legal name" k="legal_name" />
                <Field label="Registration number" k="registration_id" />
                <Field label="Federation" k="federation_name" />
                <Field label="Federation ID" k="federation_id" />
                <Field label="Founded" k="founded_year" type="number" />
                <Field label="Teams" k="teams_count" type="number" />
                <Field label="Registered athletes" k="registered_athletes" type="number"
                       hint="This is also your nomination budget." />
              </div>
            )}

            <div className="rounded border border-line-strong bg-panel p-4">
              <p className="cap">Proof</p>
              <p className="meta mt-1">
                A page a stranger can open and find {role === 'athlete' ? 'your name' : 'the club'} on.
                This is the single biggest factor in the result.
              </p>
              <div className="mt-3 grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="cap">Kind</span>
                  <select className="field mt-1" value={gate.proof_kind}
                          onChange={(e) => setGateField('proof_kind', e.target.value)}>
                    {PROOF_KINDS.map((k) => (
                      <option key={k} value={k}>{k === 'none' ? 'none yet' : k}</option>
                    ))}
                  </select>
                </label>
                <Field label="Link" k={role === 'athlete' ? 'proof_url' : 'roster_url'}
                       placeholder="https://" />
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <button className="btn-go" disabled={busy}>
                {busy ? 'Submitting…' : 'Submit for review'}
              </button>
              <button type="button" className="btn" onClick={() => navigate(roleHome(role))}>
                Finish later
              </button>
              <span className="meta">You can edit this any time from your profile.</span>
            </div>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-ground">
      <header className="mx-auto flex h-16 max-w-[1140px] items-center px-7">
        <Link to="/">
          <Wordmark size="text-[22px]" />
        </Link>
      </header>
      <div className="mx-auto max-w-md px-7 py-10">
        <div className="flex gap-1 rounded-card border border-line bg-panel p-1">
          {(['login', 'register'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              aria-pressed={mode === m}
              className={`flex-1 rounded py-2 font-display text-[13px] font-semibold uppercase tracking-micro transition-colors ${
                mode === m ? 'bg-track text-ink' : 'text-ink-3 hover:text-ink-2'
              }`}
            >
              {m === 'login' ? 'Sign in' : 'Create account'}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="panel mt-4 space-y-4 p-6">
          {mode === 'register' && (
            <div className="space-y-2">
              <div className="cap">Account type</div>
              {ROLES.map((r) => (
                <button
                  type="button"
                  key={r.key}
                  onClick={() => setRole(r.key)}
                  className={`w-full rounded border p-3 text-left transition-colors ${
                    role === r.key ? 'border-accent bg-raised' : 'border-line hover:border-line-strong'
                  }`}
                >
                  <div className="text-sm font-medium text-ink">{r.title}</div>
                  <div className="mt-0.5 text-xs text-ink-3">{r.body}</div>
                </button>
              ))}
            </div>
          )}

          {mode === 'register' && (
            <label className="block">
              <span className="cap">Full name</span>
              <input className="field mt-1" required minLength={2} value={form.display_name} onChange={(e) => set('display_name', e.target.value)} />
            </label>
          )}
          <label className="block">
            <span className="cap">Email</span>
            <input className="field mt-1" type="email" required value={form.email} onChange={(e) => set('email', e.target.value)} />
          </label>
          <label className="block">
            <span className="cap">Password</span>
            <input className="field mt-1" type="password" required minLength={8} value={form.password} onChange={(e) => set('password', e.target.value)} />
          </label>

          {mode === 'register' && role === 'athlete' && (
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="cap">Sport</span>
                <input className="field mt-1" value={form.sport} onChange={(e) => set('sport', e.target.value)} placeholder="Athletics" />
              </label>
              <label className="block">
                <span className="cap">Country</span>
                <input className="field mt-1" value={form.country} onChange={(e) => set('country', e.target.value)} placeholder="United States" />
              </label>
            </div>
          )}
          {mode === 'register' && role === 'sponsor' && (
            <label className="block">
              <span className="cap">Organization</span>
              <input className="field mt-1" value={form.org_name} onChange={(e) => set('org_name', e.target.value)} placeholder="Company name" />
            </label>
          )}
          {mode === 'register' && role === 'club' && (
            <div className="space-y-3">
              <label className="block">
                <span className="cap">Club name</span>
                <input className="field mt-1" value={form.org_name} onChange={(e) => set('org_name', e.target.value)} placeholder="Meridian FC" />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="cap">Sport</span>
                  <input className="field mt-1" value={form.sport} onChange={(e) => set('sport', e.target.value)} placeholder="Football" />
                </label>
                <label className="block">
                  <span className="cap">Country</span>
                  <input className="field mt-1" value={form.country} onChange={(e) => set('country', e.target.value)} placeholder="United Kingdom" />
                </label>
              </div>
            </div>
          )}

          {error && <div className="rounded border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-critical">{error}</div>}
          {notice && <div className="rounded border border-ok/40 bg-ok/10 px-3 py-2 text-sm text-ok">{notice}</div>}

          <button className="btn-go w-full" disabled={busy}>
            {busy ? 'Working…' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <div className="panel mt-4 p-4">
          <div className="cap">Demo accounts</div>
          <div className="mt-2 space-y-1 text-xs text-ink-2">
            {DEMO.map((d) => (
              <div key={d.email} className="flex justify-between">
                <span>{d.label}</span>
                <button className="tnum text-accent hover:underline" type="button"
                        onClick={() => { set('email', d.email); set('password', 'stride123'); setMode('login') }}>
                  {d.email}
                </button>
              </div>
            ))}
            <div className="pt-1 text-ink-3">Shared password: stride123</div>
          </div>
        </div>
      </div>
    </div>
  )
}
