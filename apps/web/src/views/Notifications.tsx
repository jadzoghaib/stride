/** Notifications.
 *
 *  A page rather than a dropdown, for the same reason the inbox is one. Both
 *  are lists that arrive over time and that you want history on; a panel that
 *  closes the moment you look elsewhere can show you the newest three and
 *  nothing else, and it has nowhere to put the ones you have already read.
 *
 *  Everything here is marked read on arrival. That is the honest reading of
 *  what opening the page means — you have now seen them — and it is why the
 *  bell's count is cleared here rather than by a separate "mark all read"
 *  control that would only ever be clicked immediately after arriving.
 */
import { BadgeCheck, Bell, Briefcase, Mail, MessageSquare, Radio, ShieldCheck, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyNote, LoadError, PageHeader, PageLoading } from '../components/ui'
import { api, errorText } from '../lib/api'

interface Note {
  id: number
  kind: string
  title: string
  body: string
  link: string
  at: string
  read: boolean
}

/** A notification's kind, drawn. Defaulting everything to a bell would make the
 *  column decoration; these say what *sort* of thing arrived before the title is
 *  read, which is the only reason to spend the space. */
const ICON: Record<string, typeof Bell> = {
  offer: Briefcase,
  deal: Briefcase,
  message: MessageSquare,
  fan_post: Users,
  subscription: Radio,
  follow: Radio,
  admission: ShieldCheck,
  club_invite: BadgeCheck,
  club: BadgeCheck,
}

function when(iso: string): string {
  const at = new Date(iso)
  const mins = Math.round((Date.now() - at.getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  if (mins < 60 * 24) return `${Math.round(mins / 60)}h ago`
  if (mins < 60 * 24 * 7) return `${Math.round(mins / (60 * 24))}d ago`
  return at.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default function Notifications() {
  const [items, setItems] = useState<Note[] | null>(null)
  const [unread, setUnread] = useState(0)
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    api.get<{ unread: number; items: Note[] }>('/api/notifications?limit=100')
      .then(async (r) => {
        if (!alive) return
        // The unread count is captured *before* clearing, so the page can still
        // show which rows were new — marking them read must not erase the only
        // signal saying which ones you had not seen.
        setItems(r.items)
        setUnread(r.unread)
        if (r.unread > 0) {
          try { await api.post('/api/notifications/read') } catch { /* the badge is not worth a banner */ }
        }
      })
      .catch((e) => { if (alive) setError(errorText(e)) })
    return () => { alive = false }
  }, [])

  if (!items) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      <PageHeader
        eyebrow="Signals"
        title="Notifications"
        lede="Everything the system raised for you — offers, replies, wall posts and review decisions."
        aside={
          <span className="meta">
            {items.length} notification{items.length === 1 ? '' : 's'}
            {unread > 0 ? ` · ${unread} new` : ''}
          </span>
        }
      />

      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      {items.length === 0 ? (
        <EmptyNote text="Nothing yet. Offers, messages and decisions about your account land here." />
      ) : (
        <div className="space-y-2">
          {items.map((n) => {
            const Icon = ICON[n.kind] ?? Bell
            const row = (
              <div className={`panel flex items-start gap-3 p-3.5 ${n.link ? 'panel-hover' : ''}`}>
                <span className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full
                                  ${n.read ? 'bg-raised text-ink-3' : 'bg-accent/15 text-accent'}`}>
                  <Icon size={15} strokeWidth={1.9} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className={`truncate ${n.read ? 'text-ink-2' : 'font-medium text-ink'}`}>
                      {n.title}
                    </span>
                    <span className="meta ml-auto shrink-0">{when(n.at)}</span>
                  </div>
                  {n.body && <p className="mt-0.5 text-sm text-ink-3">{n.body}</p>}
                </div>
                {!n.read && <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />}
              </div>
            )
            return n.link
              ? <Link key={n.id} to={n.link} className="block">{row}</Link>
              : <div key={n.id}>{row}</div>
          })}
        </div>
      )}

      <p className="meta mt-6">
        Messages from a person live in the <Link to="/inbox" className="text-accent hover:underline">inbox</Link>.
        This page is what the system raised on your behalf.
      </p>
    </div>
  )
}
