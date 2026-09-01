import { useEffect, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Shell from './components/Shell'
import { PageLoading } from './components/ui'
import { AuthProvider, roleHome, useAuth } from './lib/auth'
import { ToastProvider } from './lib/toast'
import Operations from './views/admin/Operations'
import ReviewQueue from './views/admin/ReviewQueue'
import Legal from './views/legal/Legal'
import YourData from './views/legal/YourData'
import AthletePublicView from './views/AthletePublic'
import Auth from './views/Auth'
import Directory from './views/Directory'
import MyClubs from './views/athlete/MyClubs'
import Inbox from './views/Inbox'
import Notifications from './views/Notifications'
import ClubPublic from './views/ClubPublic'
import Landing from './views/Landing'
import NotFound from './views/NotFound'
import ClubDashboard from './views/club/Dashboard'
import AthleteContent from './views/athlete/Content'
import ClubEligibility from './views/club/Eligibility'
import AthleteApplication from './views/athlete/Application'
import AthleteDashboard from './views/athlete/Dashboard'
import AthleteDeals from './views/athlete/Deals'
import AthleteProfile from './views/athlete/Profile'
import Discover from './views/fan/Discover'
import Feed from './views/fan/Feed'
import AthleteEvidence from './views/sponsor/AthleteEvidence'
import CampaignAnalytics from './views/sponsor/CampaignAnalytics'
import CampaignMatches from './views/sponsor/CampaignMatches'
import SponsorCampaigns from './views/sponsor/Campaigns'
import SponsorPipeline from './views/sponsor/Pipeline'

function Guard({ roles, children }: { roles: string[]; children: ReactNode }) {
  const { me, loading } = useAuth()
  // the session probe uses the same skeleton every other load does, rather than
  // a bare line of text — the shell is what is loading, so the shell is shown
  if (loading) {
    return (
      <Shell>
        <div className="pt-8">
          <PageLoading />
        </div>
      </Shell>
    )
  }
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

          <Route path="/athletes" element={<Public><Directory /></Public>} />
          <Route path="/athletes/:slug" element={<Public><AthletePublicView /></Public>} />
          <Route path="/clubs" element={<Public><Directory /></Public>} />
          <Route path="/clubs/:slug" element={<Public><ClubPublic /></Public>} />
          <Route path="/club" element={<Guard roles={['club']}><ClubDashboard /></Guard>} />
          <Route path="/club/eligibility" element={<Guard roles={['club']}><ClubEligibility /></Guard>} />

          <Route path="/athlete" element={<Guard roles={['athlete']}><AthleteDashboard /></Guard>} />
          <Route path="/athlete/deals" element={<Guard roles={['athlete']}><AthleteDeals /></Guard>} />
          <Route path="/athlete/profile" element={<Guard roles={['athlete']}><AthleteProfile /></Guard>} />
          <Route path="/athlete/content" element={<Guard roles={['athlete']}><AthleteContent /></Guard>} />
          <Route path="/athlete/clubs" element={<Guard roles={['athlete']}><MyClubs /></Guard>} />
          <Route path="/athlete/application" element={<Guard roles={['athlete']}><AthleteApplication /></Guard>} />

          <Route path="/sponsor" element={<Guard roles={['sponsor']}><SponsorCampaigns /></Guard>} />
          <Route path="/sponsor/campaigns/:id" element={<Guard roles={['sponsor']}><CampaignMatches /></Guard>} />
          <Route path="/sponsor/campaigns/:id/analytics" element={<Guard roles={['sponsor']}><CampaignAnalytics /></Guard>} />
          <Route path="/sponsor/athletes/:slug" element={<Guard roles={['sponsor']}><AthleteEvidence /></Guard>} />
          <Route path="/sponsor/pipeline" element={<Guard roles={['sponsor']}><SponsorPipeline /></Guard>} />

          {/* These two lists mirror the API exactly: /api/discover admits admin,
              /api/feed does not (a following feed needs follows, which an admin
              account has none of). A client guard that is more permissive than
              require_role just routes people to a 403. */}
          <Route path="/inbox" element={<Guard roles={['athlete', 'club', 'sponsor', 'fan', 'admin']}><Inbox /></Guard>} />
          <Route path="/notifications" element={<Guard roles={['athlete', 'club', 'sponsor', 'fan', 'admin']}><Notifications /></Guard>} />
          <Route path="/discover" element={<Guard roles={['fan', 'athlete', 'sponsor', 'admin']}><Discover /></Guard>} />
          <Route path="/feed" element={<Guard roles={['fan', 'athlete', 'sponsor']}><Feed /></Guard>} />

          <Route path="/admin" element={<Guard roles={['admin']}><Operations /></Guard>} />
          <Route path="/admin/review" element={<Guard roles={['admin']}><ReviewQueue /></Guard>} />

          {/* Public on purpose: someone deciding whether to hand over their
              social data must be able to read the terms before signing up. */}
          <Route path="/legal/data" element={<Public><YourData /></Public>} />
          <Route path="/legal/:doc" element={<Public><Legal /></Public>} />

          <Route path="*" element={<Public><NotFound /></Public>} />
        </Routes>
      </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  )
}
