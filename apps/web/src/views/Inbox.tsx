/** Direct messages.
 *
 *  Two panes rather than two routes: the list is short and the thread is the
 *  thing you came for, so selecting a conversation should not cost a page load
 *  or lose your place in the list.
 *
 *  There is no "new message" button here on purpose. A conversation starts from
 *  the person — the envelope on their card or their profile — because who you
 *  may write to is a property of your relationship with them, and a blank
 *  recipient field invites a refusal instead of explaining one.
 */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, EmptyNote, LoadError, PageHeader, PageLoading } from '../components/ui'
import { api, errorText } from '../lib/api'

interface Correspondent { id: number; display_name: string; role: string; slug: string | null }
interface Thread { id: number; with: Correspondent; last_message: string; last_at: string; unread: number }
interface Message { id: number; body: string; at: string; mine: boolean }

function stamp(iso: string): string {
  const at = new Date(iso)
  const today = new Date().toDateString() === at.toDateString()
  return today
    ? at.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
    : at.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default function Inbox() {
  const [threads, setThreads] = useState<Thread[] | null>(null)
  const [open, setOpen] = useState<{ id: number; with: Correspondent; messages: Message[] } | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')

  const load = () => api.get<Thread[]>('/api/inbox').then(setThreads).catch((e) => setError(errorText(e)))
  useEffect(() => { void load() }, [])

  const openThread = async (id: number) => {
    try {
      setOpen(await api.get(`/api/inbox/${id}`))
      await load()          // reading clears the unread count on the server
    } catch (e) { setError(errorText(e)) }
  }

  const send = async () => {
    if (!open || !draft.trim()) return
    try {
      await api.post('/api/messages', { to_user: open.with.id, body: draft.trim() })
      setDraft('')
      await openThread(open.id)
    } catch (e) { setError(errorText(e)) }
  }

  if (!threads) return error ? <LoadError text={error} /> : <PageLoading />

  const unread = threads.reduce((n, t) => n + t.unread, 0)

  return (
    <div>
      <PageHeader
        eyebrow="Messages"
        title="Inbox"
        lede="Offers, questions and everything else that arrives from a person rather than from the system."
        aside={<span className="meta">{threads.length} conversation{threads.length === 1 ? '' : 's'}
          {unread > 0 ? ` · ${unread} unread` : ''}</span>}
      />

      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      {threads.length === 0 ? (
        <EmptyNote text="No conversations yet. Message someone from their profile — the envelope appears wherever you are allowed to write to them." />
      ) : (
        <div className="grid gap-4 md:grid-cols-[19rem_1fr]">
          <div className="space-y-2">
            {threads.map((t) => (
              <button key={t.id} onClick={() => void openThread(t.id)}
                      className={`panel w-full p-3 text-left ${
                        open?.id === t.id ? 'border-accent' : 'panel-hover'}`}>
                <div className="flex items-center gap-2.5">
                  <Avatar name={t.with.display_name} size={32} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="truncate font-medium text-ink">{t.with.display_name}</span>
                      <span className="meta ml-auto shrink-0">{stamp(t.last_at)}</span>
                    </div>
                    <div className="truncate text-xs text-ink-3">{t.last_message}</div>
                  </div>
                  {t.unread > 0 && (
                    <span className="tnum rounded-full bg-accent px-1.5 py-0.5 text-label font-bold text-accent-on">
                      {t.unread}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>

          <div className="panel flex min-h-[24rem] flex-col p-4">
            {!open ? (
              <p className="meta m-auto">Pick a conversation.</p>
            ) : (
              <>
                <div className="flex items-center gap-2 border-b border-line pb-3">
                  <Avatar name={open.with.display_name} size={30} />
                  {open.with.slug ? (
                    <Link to={`/${open.with.role === 'club' ? 'clubs' : 'athletes'}/${open.with.slug}`}
                          className="font-medium text-ink hover:text-accent">
                      {open.with.display_name}
                    </Link>
                  ) : (
                    <span className="font-medium text-ink">{open.with.display_name}</span>
                  )}
                  <span className="cap text-ink-3">{open.with.role}</span>
                </div>

                <div className="flex-1 space-y-2 overflow-y-auto py-4">
                  {open.messages.map((m) => (
                    <div key={m.id} className={`flex ${m.mine ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] rounded px-3 py-2 text-sm ${
                        m.mine ? 'bg-accent text-accent-on' : 'bg-raised text-ink-2'}`}>
                        <p className="whitespace-pre-line">{m.body}</p>
                        <p className={`mt-1 text-label ${m.mine ? 'text-accent-on/70' : 'text-ink-3'}`}>
                          {stamp(m.at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex items-end gap-2 border-t border-line pt-3">
                  <textarea className="field min-h-[3rem] flex-1" value={draft} rows={2}
                            placeholder={`Message ${open.with.display_name}`}
                            onChange={(e) => setDraft(e.target.value)} />
                  <button className="btn-go" disabled={!draft.trim()} onClick={() => void send()}>
                    Send
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
