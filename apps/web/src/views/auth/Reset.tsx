/** /reset?token=… — the link from the reset email.
 *
 *  Setting the password signs every other device out and signs this one in,
 *  which is the right response to both "I forgot it" and "somebody has it".
 */

import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ThemeToggle, Wordmark } from '../../components/Shell'
import { api, errorText } from '../../lib/api'
import { roleHome, useAuth } from '../../lib/auth'
import type { Me } from '../../types'

export default function Reset() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()
  const { refresh } = useAuth()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(token ? '' : 'This link is missing its token.')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password !== confirm) { setError('The two passwords do not match.'); return }
    setBusy(true); setError('')
    try {
      const me = await api.post<Me>('/api/auth/reset', { token, password })
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
      <header className="mx-auto flex h-16 max-w-page items-center justify-between px-7">
        <Link to="/"><Wordmark size="text-title" /></Link>
        <ThemeToggle />
      </header>
      <main className="mx-auto max-w-md px-7 py-16">
        <p className="cap">Password reset</p>
        <h1 className="mt-3 text-head font-semibold text-ink">Choose a new password</h1>
        <p className="mt-3 text-ink-2">
          Every other device signed in to this account will be signed out. This one stays in.
        </p>
        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block">
            <span className="cap">New password</span>
            <input className="field mt-1" type="password" required minLength={8} autoComplete="new-password"
                   value={password} onChange={(e) => setPassword(e.target.value)} />
            <span className="meta mt-1 block">At least 8 characters.</span>
          </label>
          <label className="block">
            <span className="cap">Again</span>
            <input className="field mt-1" type="password" required minLength={8} autoComplete="new-password"
                   value={confirm} onChange={(e) => setConfirm(e.target.value)} />
          </label>
          {error && <div className="rounded border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-critical">{error}</div>}
          <button className="btn-go w-full" disabled={busy || !token}>
            {busy ? 'Working…' : 'Set password and sign in'}
          </button>
        </form>
        <p className="meta mt-6">
          Links work once and expire after two hours. <Link to="/auth?mode=forgot" className="text-accent-ink hover:underline">Ask for a new one</Link>.
        </p>
      </main>
    </div>
  )
}
