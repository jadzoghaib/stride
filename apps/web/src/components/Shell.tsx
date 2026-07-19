/** Role-aware application shell: top bar with wordmark, role navigation, session. */

import { BarChart3, Briefcase, Compass, FileSearch, LayoutDashboard, LogOut, Radio, Shield, Users } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { roleHome, useAuth } from '../lib/auth'
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

export function Wordmark({ size = 'text-lg' }: { size?: string }) {
  return (
    <span className={`font-semibold tracking-tight ${size}`}>
      <span className="text-mist-100">ST</span>
      <span className="wave-text">RIDE</span>
    </span>
  )
}

export default function Shell({ children }: { children: ReactNode }) {
  const { me, logout } = useAuth()
  const navigate = useNavigate()
  const items = me ? NAV[me.role] ?? [] : []

  return (
    <div className="min-h-screen wave-field">
      <header className="sticky top-0 z-20 border-b border-line bg-ink-950/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-8 px-5">
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
                  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${
                    isActive ? 'bg-ink-800 text-mist-100' : 'text-mist-400 hover:text-mist-200'
                  }`
                }
              >
                <Icon size={15} strokeWidth={1.8} />
                <span className="hidden md:inline">{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {me ? (
              <>
                <span className="chip capitalize">{me.role}</span>
                <Avatar name={me.display_name} size={30} />
                <button
                  className="text-mist-400 hover:text-mist-200"
                  title="Sign out"
                  aria-label="Sign out"
                  onClick={async () => {
                    await logout()
                    navigate('/')
                  }}
                >
                  <LogOut size={16} strokeWidth={1.8} />
                </button>
              </>
            ) : (
              <Link to="/auth" className="btn-primary">
                Sign in
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-5 py-8">{children}</main>
    </div>
  )
}
