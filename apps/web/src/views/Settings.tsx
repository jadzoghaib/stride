/** /settings — the account itself, as distinct from the profile.
 *
 *  A profile is what other people see; this is what only the account holder
 *  can do: prove the address, change the password, sign out everywhere, and
 *  reach the data-rights page. Every role gets the same page because every
 *  role has the same account.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageHeader, Section } from '../components/ui'
import { api, errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useToast } from '../lib/toast'

export default function Settings() {
  const { me, refresh, logout } = useAuth()
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [resent, setResent] = useState(false)

  if (!me) return null

  const changePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (next !== again) { setError('The two new passwords do not match.'); return }
    setBusy(true); setError('')
    try {
      await api.post('/api/auth/password', { current_password: current, new_password: next })
      setCurrent(''); setNext(''); setAgain('')
      toast('Password changed. Every other device has been signed out.')
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  const resend = async () => {
    await api.post('/api/auth/resend-verification')
    setResent(true)
    toast('Confirmation email queued')
  }

  const signOutEverywhere = async () => {
    await api.post('/api/auth/logout-all')
    await logout()
    window.location.assign('/')
  }

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Account"
        title="Settings"
        lede="The account behind your profile: your address, your password, your sessions, your data."
        aside={<span className="tag capitalize">{me.role}</span>}
      />

      <Section title="Email" aside={me.email_verified
        ? <span className="tag tag-ok">confirmed</span>
        : <span className="tag tag-warn">not confirmed</span>}>
        <div className="panel p-5">
          <p className="text-body text-ink">{me.email}</p>
          {me.email_verified ? (
            <p className="mt-2 text-body text-ink-2">This address is confirmed.</p>
          ) : (
            <>
              <p className="mt-2 text-body text-ink-2">
                We sent a confirmation link when you registered. Open it to confirm this address is yours —
                it is how a password reset reaches you.
              </p>
              <button className="btn mt-4" onClick={resend} disabled={resent}>
                {resent ? 'Sent again' : 'Send the link again'}
              </button>
              <p className="meta mt-3">
                In this demo build nothing is actually mailed: an administrator can read the queued message,
                link included, from Operations → Outbox.
              </p>
            </>
          )}
        </div>
      </Section>

      <Section title="Password">
        <form onSubmit={changePassword} className="panel space-y-4 p-5">
          <label className="block">
            <span className="cap">Current password</span>
            <input className="field mt-1" type="password" required autoComplete="current-password"
                   value={current} onChange={(e) => setCurrent(e.target.value)} />
          </label>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="cap">New password</span>
              <input className="field mt-1" type="password" required minLength={8} autoComplete="new-password"
                     value={next} onChange={(e) => setNext(e.target.value)} />
            </label>
            <label className="block">
              <span className="cap">Again</span>
              <input className="field mt-1" type="password" required minLength={8} autoComplete="new-password"
                     value={again} onChange={(e) => setAgain(e.target.value)} />
            </label>
          </div>
          {error && <div className="rounded border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-critical">{error}</div>}
          <div className="flex items-center justify-between gap-4">
            <span className="meta">Changing it signs out every other device. This one stays in.</span>
            <button className="btn-go" disabled={busy}>{busy ? 'Working…' : 'Change password'}</button>
          </div>
        </form>
      </Section>

      <Section title="Sessions">
        <div className="panel flex flex-wrap items-center justify-between gap-4 p-5">
          <p className="text-body text-ink-2">
            Lost a device, or signed in somewhere you should not have? This ends every session, including this one.
          </p>
          <button className="btn" onClick={signOutEverywhere}>Sign out everywhere</button>
        </div>
      </Section>

      <Section title="Your data">
        <div className="panel p-5">
          <p className="text-body text-ink-2">
            What Stride holds about you and the controls over it — including which of your rights are live
            today and which are not yet built.
          </p>
          <Link to="/legal/data" className="btn mt-4 inline-flex">Open your data</Link>
          <p className="meta mt-3">
            Terms accepted: {me.accepted_policy_version ? `version ${me.accepted_policy_version}` : 'not recorded'}.
          </p>
        </div>
      </Section>
    </div>
  )
}
