/** Role-aware application shell.
 *
 *  A left rail when signed in, a bar when signed out. The rail carries the
 *  four always-available things as icons — home, inbox, notifications, theme —
 *  then the role's sections as a list, then the account. The active section is
 *  marked with an amber edge, the same rule that closes a board header, so the
 *  navigation and the pages read as one system. */

import { BadgeCheck, BarChart3, Bell, Briefcase, ClipboardCheck, Compass, FileSearch, LayoutDashboard, LogOut, Mail, Moon, Radio, Shield, Sun, Users } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { roleHome, useAuth } from '../lib/auth'
import { useTheme } from '../lib/theme'
import Footer from './Footer'
import { Avatar } from './ui'

interface NotificationItem {
  id: number; kind: string; title: string; body: string; link: string; read: boolean
}

const NAV: Record<string, { to: string; label: string; icon: typeof Compass }[]> = {
  athlete: [
    { to: '/athlete', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/athlete/deals', label: 'Deals', icon: Briefcase },
    { to: '/athlete/content', label: 'Content', icon: BadgeCheck },
    { to: '/athlete/profile', label: 'Profile', icon: Users },
    { to: '/athletes', label: 'Directory', icon: Compass },
    { to: '/clubs', label: 'Clubs', icon: Shield },
  ],
  sponsor: [
    { to: '/sponsor', label: 'Campaigns', icon: BarChart3 },
    { to: '/sponsor/pipeline', label: 'Pipeline', icon: Briefcase },
    { to: '/athletes', label: 'Directory', icon: Compass },
    { to: '/clubs', label: 'Clubs', icon: Shield },
  ],
  fan: [
    // No Clubs tab: a separate directory of clubs is a second place to search
    // for the same thing. Discover filters by athlete or club instead, so there
    // is one search box and one set of filters.
    { to: '/discover', label: 'Discover', icon: Compass },
    { to: '/feed', label: 'Following', icon: Radio },
  ],
  club: [
    { to: '/club', label: 'Club HQ', icon: LayoutDashboard },
    { to: '/athletes', label: 'Directory', icon: Compass },
    { to: '/clubs', label: 'Clubs', icon: Shield },
  ],
  admin: [
    { to: '/athletes', label: 'Directory', icon: Compass },
    { to: '/clubs', label: 'Clubs', icon: Shield },
    { to: '/admin/review', label: 'Review', icon: ClipboardCheck },
    { to: '/admin', label: 'Operations', icon: FileSearch },
  ],
}

export function Wordmark({ size = 'text-[22px]' }: { size?: string }) {
  return (
    <span className={`flex items-baseline gap-2 font-display font-bold tracking-board text-ink ${size}`}>
      <i className="block h-[3px] w-5 bg-accent" />
      STRIDE
    </span>
  )
}

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  return (
    <button
      onClick={toggle}
      className="text-ink-3 transition-colors hover:text-ink"
      title={`Switch to ${next} theme`}
      aria-label={`Switch to ${next} theme`}
    >
      {theme === 'dark' ? <Sun size={16} strokeWidth={1.9} /> : <Moon size={16} strokeWidth={1.9} />}
    </button>
  )
}


/** Envelope and bell, for every signed-in role.
 *
 *  Counts are fetched once on mount rather than polled: this is a demo without
 *  a socket, and a timer that re-fetched every few seconds would spend the
 *  whole session making requests to discover nothing changed. The counts
 *  refresh on navigation, which is when a reader would look.
 */
function Signals() {
  const [unreadMail, setUnreadMail] = useState(0)
  const [unreadBells, setUnreadBells] = useState(0)
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<NotificationItem[]>([])
  const location = useLocation()

  useEffect(() => {
    api.get<{ id: number; unread: number }[]>('/api/inbox')
      .then((t) => setUnreadMail(t.reduce((n, x) => n + (x.unread ?? 0), 0)))
      .catch(() => setUnreadMail(0))
    api.get<{ unread: number; items: NotificationItem[] }>('/api/notifications')
      .then((r) => { setUnreadBells(r.unread); setItems(r.items) })
      .catch(() => setUnreadBells(0))
  }, [location.pathname])

  const readAll = async () => {
    try {
      await api.post('/api/notifications/read')
      setUnreadBells(0)
      setItems((list) => list.map((i) => ({ ...i, read: true })))
    } catch { /* the badge is not worth an error banner */ }
  }

  return (
    <>
      <Link to="/inbox" className="relative text-ink-3 transition-colors hover:text-ink"
            title="Inbox" aria-label={`Inbox${unreadMail ? `, ${unreadMail} unread` : ''}`}>
        <Mail size={16} strokeWidth={1.9} />
        {unreadMail > 0 && <Dot n={unreadMail} />}
      </Link>

      <div className="relative">
        <button className="relative text-ink-3 transition-colors hover:text-ink"
                title="Notifications"
                aria-label={`Notifications${unreadBells ? `, ${unreadBells} unread` : ''}`}
                onClick={() => { setOpen((v) => !v); if (!open && unreadBells) void readAll() }}>
          <Bell size={16} strokeWidth={1.9} />
          {unreadBells > 0 && <Dot n={unreadBells} />}
        </button>
        {open && (
          <div className="panel absolute right-0 z-30 mt-2 max-h-96 w-80 overflow-y-auto p-2">
            {items.length === 0 ? (
              <p className="meta p-3">Nothing yet.</p>
            ) : (
              items.map((n) => (
                <Link key={n.id} to={n.link || '#'} onClick={() => setOpen(false)}
                      className="block rounded p-2.5 hover:bg-raised">
                  <div className="text-sm font-medium text-ink">{n.title}</div>
                  {n.body && <div className="mt-0.5 text-xs text-ink-3">{n.body}</div>}
                </Link>
              ))
            )}
          </div>
        )}
      </div>
    </>
  )
}

function Dot({ n }: { n: number }) {
  return (
    <span className="tnum absolute -right-1.5 -top-1.5 rounded-full bg-accent px-1 text-[10px]
                     font-bold leading-[1.35] text-accent-on">
      {n > 9 ? '9+' : n}
    </span>
  )
}

export default function Shell({ children }: { children: ReactNode }) {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const items = me ? NAV[me.role] ?? [] : []
  const hasChildTab = (to: string) => items.some((i) => i.to !== to && i.to.startsWith(to + '/'))

  // Signed out, the product is a landing page and a directory: a rail of
  // sections nobody can open would be furniture. The bar stays until there is
  // a session to navigate.
  if (!me) {
    return (
      <div className="min-h-screen bg-ground">
        <header className="sticky top-0 z-20 border-b border-line bg-ground/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-[1140px] items-center gap-8 px-7">
            <Link to="/"><Wordmark /></Link>
            <div className="ml-auto flex items-center gap-3">
              <ThemeToggle />
              <Link to="/auth" className="btn-go">Sign in</Link>
            </div>
          </div>
        </header>
        <main className="stride-main">{children}</main>
        <Footer />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-ground md:flex">
      {/* ── the rail ───────────────────────────────────────────────────────
          A sidebar rather than a top bar, because this product is read one
          long column at a time — a wall, a pipeline, a queue — and vertical
          space is the scarce thing on every one of those pages. */}
      <aside className="sticky top-0 z-20 hidden h-screen w-[15rem] shrink-0 flex-col
                        border-r border-line bg-panel px-4 py-5 md:flex">
        <Link to={roleHome(me.role)} className="mb-6 block px-2"><Wordmark /></Link>

        {/* the four things that are always one click away, as icons */}
        <div className="mb-6 flex items-center gap-2">
          <RailIcon to={roleHome(me.role)} label="Home"><LayoutDashboard size={17} strokeWidth={1.9} /></RailIcon>
          <Signals />
          <ThemeToggle />
        </div>

        <nav className="flex flex-1 flex-col gap-0.5">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={hasChildTab(to)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded px-3 py-2 font-display text-[14px] font-semibold
                 uppercase tracking-micro transition-colors ${
                  isActive
                    ? 'bg-raised text-ink shadow-[inset_2px_0_0_rgb(var(--c-accent))]'
                    : 'text-ink-3 hover:bg-raised hover:text-ink-2'}`
              }
            >
              <Icon size={16} strokeWidth={1.9} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="mt-4 flex items-center gap-2.5 border-t border-line pt-4">
          <Avatar name={me.display_name} size={32} />
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-medium text-ink">{me.display_name}</div>
            <div className="cap text-ink-3">{me.role}</div>
          </div>
          <button className="text-ink-3 transition-colors hover:text-ink" title="Sign out"
                  aria-label="Sign out"
                  onClick={async () => { await logout(); navigate('/') }}>
            <LogOut size={16} strokeWidth={1.9} />
          </button>
        </div>
      </aside>

      {/* the same set, as a bar, on a phone */}
      <header className="sticky top-0 z-20 border-b border-line bg-ground/90 backdrop-blur md:hidden">
        <div className="flex h-14 items-center gap-3 px-4">
          <Link to={roleHome(me.role)}><Wordmark /></Link>
          <div className="ml-auto flex items-center gap-3">
            <Signals />
            <ThemeToggle />
            <button className="text-ink-3" aria-label="Sign out"
                    onClick={async () => { await logout(); navigate('/') }}>
              <LogOut size={16} strokeWidth={1.9} />
            </button>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-2">
          {items.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={hasChildTab(to)}
                     className={({ isActive }) =>
                       `flex shrink-0 items-center gap-1.5 rounded px-3 py-1.5 font-display
                        text-[12px] font-semibold uppercase tracking-micro ${
                         isActive ? 'bg-raised text-ink' : 'text-ink-3'}`}>
              <Icon size={14} strokeWidth={1.9} />
              {label}
            </NavLink>
          ))}
        </nav>
      </header>

      <div className="min-w-0 flex-1">
        <main className="stride-main">{children}</main>
        <Footer />
      </div>
    </div>
  )
}

function RailIcon({ to, label, children }: { to: string; label: string; children: ReactNode }) {
  return (
    <Link to={to} title={label} aria-label={label}
          className="flex h-9 w-9 items-center justify-center rounded border border-line
                     text-ink-3 transition-colors hover:text-ink">
      {children}
    </Link>
  )
}
