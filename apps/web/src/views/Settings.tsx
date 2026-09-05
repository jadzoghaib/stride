/** /settings — the account itself, as distinct from the profile.
 *
 *  A profile is what other people see; this is what only the account holder
 *  can do: prove the address, change the password, sign out everywhere, take
 *  their data out, and end the account. Every role gets the same page because
 *  every role has the same account.
 */

import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { PageHeader, Section } from '../components/ui'
import { api, errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { useToast } from '../lib/toast'

export default function Settings() {
  const { me, logout } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [again, setAgain] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [resent, setResent] = useState(false)
  const [delPassword, setDelPassword] = useState('')
  const [delWord, setDelWord] = useState('')
  const [delError, setDelError] = useState('')
  const [deleting, setDeleting] = useState(false)

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

  const deleteAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    setDeleting(true); setDelError('')
    try {
      await api.post('/api/account/delete', { password: delPassword, confirm: delWord })
      // the server has already cleared the cookie; this just drops the client copy
      await logout().catch(() => undefined)
      navigate('/', { replace: true })
    } catch (err) {
      setDelError(errorText(err))
      setDeleting(false)
    }
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
            What Stride holds about you and the controls over it — including a one-click export of all of it.
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            <a href="/api/account/export" download={`stride-export-${me.id}.json`} className="btn">Download my data</a>
            <Link to="/legal/data" className="btn">Every control, explained</Link>
          </div>
          <p className="meta mt-3">
            Terms accepted: {me.accepted_policy_version ? `version ${me.accepted_policy_version}` : 'not recorded'}.
          </p>
        </div>
      </Section>

      {me.role !== 'admin' && (
        <Section title="Delete account" aside={<span className="tag tag-critical">permanent</span>}>
          <form onSubmit={deleteAccount} className="panel space-y-4 border-critical/40 p-5">
            <p className="text-body text-ink-2">
              Your account, profile, posts, follows, subscriptions, votes, wall posts and notifications are
              removed, and your side of every conversation is blanked. Deal and commitment records stay, with
              your name removed, where accounting or dispute duties require it — as the Privacy Policy says.
              This cannot be undone.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="cap">Your password</span>
                <input className="field mt-1" type="password" required autoComplete="current-password"
                       value={delPassword} onChange={(e) => setDelPassword(e.target.value)} />
              </label>
              <label className="block">
                <span className="cap">Type DELETE to confirm</span>
                <input className="field mt-1" required autoComplete="off" spellCheck={false}
                       value={delWord} onChange={(e) => setDelWord(e.target.value)} />
              </label>
            </div>
            {delError && <div className="rounded border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-critical">{delError}</div>}
            <div className="flex justify-end">
              <button className="btn border-critical/60 text-critical hover:border-critical hover:bg-critical/10 hover:text-critical"
                      disabled={deleting || delWord.trim().toUpperCase() !== 'DELETE'}>
                {deleting ? 'Deleting…' : 'Delete my account'}
              </button>
            </div>
          </form>
        </Section>
      )}
    </div>
  )
}
