import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Shell from './components/Shell'
import { AuthProvider, roleHome, useAuth } from './lib/auth'
import { ToastProvider } from './lib/toast'
import AthletePublicView from './views/AthletePublic'
import AthletesDirectory from './views/AthletesDirectory'
import Auth from './views/Auth'
import ClubPublic from './views/ClubPublic'
import ClubsDirectory from './views/ClubsDirectory'
import Landing from './views/Landing'
import NotFound from './views/NotFound'
import ClubDashboard from './views/club/Dashboard'
import AthleteDashboard from './views/athlete/Dashboard'
import AthleteDeals from './views/athlete/Deals'
import AthleteProfile from './views/athlete/Profile'
import Discover from './views/fan/Discover'
import Feed from './views/fan/Feed'
import AthleteEvidence from './views/sponsor/AthleteEvidence'
import CampaignMatches from './views/sponsor/CampaignMatches'
import SponsorCampaigns from './views/sponsor/Campaigns'
import SponsorPipeline from './views/sponsor/Pipeline'

function Guard({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { me, loading } = useAuth()
  if (loading) return <div className="p-8 text-mist-400">Checking session…</div>
  if (!me) return <Navigate to="/auth" replace />
  if (!roles.includes(me.role)) return <Navigate to={roleHome(me.role)} replace />
  return <Shell>{children}</Shell>
}

function Public({ children }: { children: ReactNode }) {
  return <Shell>{children}</Shell>
}

/** React Router doesn't scroll to #anchors — stat cards deep-link to sections. */
function ScrollToHash() {
  const { hash, pathname } = useLocation()
  useEffect(() => {
    if (hash) {
      // slight delay so freshly-routed views have rendered their sections
      const t = window.setTimeout(() => {
        document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth' })
      }, 60)
      return () => window.clearTimeout(t)
    }
    window.scrollTo(0, 0)
  }, [hash, pathname])
  return null
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
      <BrowserRouter>
        <ScrollToHash />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/auth" element={<Auth />} />

          <Route path="/athletes" element={<Public><AthletesDirectory /></Public>} />
          <Route path="/athletes/:slug" element={<Public><AthletePublicView /></Public>} />
          <Route path="/clubs" element={<Public><ClubsDirectory /></Public>} />
          <Route path="/clubs/:slug" element={<Public><ClubPublic /></Public>} />
          <Route path="/club" element={<Guard roles={['club']}><ClubDashboard /></Guard>} />

          <Route path="/athlete" element={<Guard roles={['athlete']}><AthleteDashboard /></Guard>} />
          <Route path="/athlete/deals" element={<Guard roles={['athlete']}><AthleteDeals /></Guard>} />
          <Route path="/athlete/profile" element={<Guard roles={['athlete']}><AthleteProfile /></Guard>} />

          <Route path="/sponsor" element={<Guard roles={['sponsor']}><SponsorCampaigns /></Guard>} />
          <Route path="/sponsor/campaigns/:id" element={<Guard roles={['sponsor']}><CampaignMatches /></Guard>} />
          <Route path="/sponsor/athletes/:slug" element={<Guard roles={['sponsor']}><AthleteEvidence /></Guard>} />
          <Route path="/sponsor/pipeline" element={<Guard roles={['sponsor']}><SponsorPipeline /></Guard>} />

          <Route path="/discover" element={<Guard roles={['fan', 'athlete', 'sponsor', 'admin']}><Discover /></Guard>} />
          <Route path="/feed" element={<Guard roles={['fan', 'athlete', 'sponsor', 'admin']}><Feed /></Guard>} />

          <Route path="*" element={<Public><NotFound /></Public>} />
        </Routes>
      </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
