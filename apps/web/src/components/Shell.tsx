/** Role-aware application shell: board bar with wordmark, role navigation,
 *  theme control, session. The active tab is marked by an amber underscore —
 *  the same rule that closes the board header, so the two read as one system. */

import { BarChart3, Briefcase, Compass, FileSearch, LayoutDashboard, LogOut, Moon, Radio, Shield, Sun, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { roleHome, useAuth } from '../lib/auth'
import { useTheme } from '../lib/theme'
import { Avatar } from './ui'

const NAV: Record<string, { to: string; label: string; icon: typeof Compass }[]> = {
  athlete: [
    { to: '/athlete', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/athlete/deals', label: 'Deals', icon: Briefcase },
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
    { to: '/discover', label: 'Discover', icon: Compass },
    { to: '/feed', label: 'Following', icon: Radio },
    { to: '/clubs', label: 'Clubs', icon: Shield },
  ],
  club: [
    { to: '/club', label: 'Club HQ', icon: LayoutDashboard },
    { to: '/athletes', label: 'Directory', icon: Compass },
    { to: '/clubs', label: 'Clubs', icon: Shield },
  ],
  admin: [
    { to: '/athletes', label: 'Directory', icon: Compass },
    { to: '/clubs', label: 'Clubs', icon: Shield },
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

export default function Shell({ children }: { children: ReactNode }) {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const items = me ? NAV[me.role] ?? [] : []

  return (
    <div className="min-h-screen bg-ground">
      <header className="sticky top-0 z-20 border-b border-line bg-ground/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1140px] items-center gap-8 px-7">
          <Link to={me ? roleHome(me.role) : '/'}>
            <Wordmark />
          </Link>
          <nav className="flex items-center gap-1">
            {items.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/athlete' || to === '/sponsor'}
                className={({ isActive }) =>
                  `flex items-center gap-1.5 rounded px-3 py-1.5 font-display text-[13px] font-semibold uppercase tracking-micro transition-colors ${
                    isActive
                      ? 'bg-raised text-ink shadow-[inset_0_-2px_0_rgb(var(--c-accent))]'
                      : 'text-ink-3 hover:bg-raised hover:text-ink-2'
                  }`
                }
              >
                <Icon size={15} strokeWidth={1.9} />
                <span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <ThemeToggle />
            {me ? (
              <>
                <span className="tag capitalize">{me.role}</span>
                <Avatar name={me.display_name} size={30} />
                <button
                  className="text-ink-3 transition-colors hover:text-ink"
                  title="Sign out"
                  aria-label="Sign out"
                  onClick={async () => {
                    await logout()
                    navigate('/')
                  }}
                >
                  <LogOut size={16} strokeWidth={1.9} />
                </button>
              </>
            ) : (
              <Link to="/auth" className="btn-go">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="stride-main">{children}</main>
    </div>
  )
}
