/** /verify?token=… — the link from the confirmation email.
 *
 *  Works signed out, because the person may open it on a different device from
 *  the one they registered on. One request, one outcome, and a plain sentence
 *  either way; a spent or expired link says so instead of pretending.
 */

import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ThemeToggle, Wordmark } from '../../components/Shell'
import { api, errorText } from '../../lib/api'
import { roleHome, useAuth } from '../../lib/auth'

export default function Verify() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const { me, refresh } = useAuth()
  const [state, setState] = useState<'working' | 'done' | 'failed'>(token ? 'working' : 'failed')
  const [detail, setDetail] = useState(token ? '' : 'This link is missing its token.')
  const [email, setEmail] = useState('')

  useEffect(() => {
    if (!token) return
    api.post<{ ok: boolean; email: string }>('/api/auth/verify-email', { token })
      .then(async (r) => { setEmail(r.email); setState('done'); await refresh() })
      .catch((e) => { setDetail(errorText(e)); setState('failed') })
  }, [token]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-ground">
      <header className="mx-auto flex h-16 max-w-page items-center justify-between px-7">
        <Link to="/"><Wordmark size="text-title" /></Link>
        <ThemeToggle />
      </header>
      <main className="mx-auto max-w-md px-7 py-16">
        <p className="cap">Email confirmation</p>
        {state === 'working' && <h1 className="mt-3 text-head font-semibold text-ink">Confirming…</h1>}
        {state === 'done' && (
          <>
            <h1 className="mt-3 text-head font-semibold text-ink">Confirmed.</h1>
            <p className="mt-3 text-ink-2">
              <span className="text-ink">{email}</span> is yours. Nothing else changes — you can carry on.
            </p>
            <Link to={me ? roleHome(me.role) : '/auth'} className="btn-go mt-6 inline-flex">
              {me ? 'Back to Stride' : 'Sign in'}
            </Link>
          </>
        )}
        {state === 'failed' && (
          <>
            <h1 className="mt-3 text-head font-semibold text-ink">That link did not work.</h1>
            <p className="mt-3 text-ink-2">{detail}</p>
            <p className="mt-2 text-ink-2">
              Links work once and expire after three days. Sign in and ask for a new one from your settings.
            </p>
            <Link to="/auth" className="btn mt-6 inline-flex">Sign in</Link>
          </>
        )}
      </main>
    </div>
  )
}
