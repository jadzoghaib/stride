import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Wordmark } from '../components/Shell'
import { api, errorText } from '../lib/api'
import { roleHome, useAuth } from '../lib/auth'
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
      navigate(roleHome(me.role))
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
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
