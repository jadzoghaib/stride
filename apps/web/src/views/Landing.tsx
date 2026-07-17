import { ArrowRight, BarChart3, ShieldCheck, Signal } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { Wordmark } from '../components/Shell'
import { roleHome, useAuth } from '../lib/auth'

const PILLARS = [
  {
    icon: Signal,
    title: 'Evidence, not estimates',
    body: 'Marketability is computed from connected social platforms through a versioned formula set — audience scale, engagement quality, fit, growth, consistency. Every score can be traced to the posts and snapshots behind it.',
  },
  {
    icon: BarChart3,
    title: 'Matching that explains itself',
    body: 'Sponsors rank athletes against a specific campaign brief. Each match shows its component breakdown — audience fit against your target, budget alignment, format overlap — with plain-language reasons and caveats.',
  },
  {
    icon: ShieldCheck,
    title: 'A governed marketplace',
    body: 'Offers, acceptances, and every account action land in an audit trail. Partial data is labeled, never hidden: an athlete with one connected platform is scored on one platform.',
  },
]

export default function Landing() {
  const { me, loading } = useAuth()
  if (!loading && me) return <Navigate to={roleHome(me.role)} replace />

  return (
    <div className="min-h-screen wave-field">
      <header className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5">
        <Wordmark size="text-xl" />
        <Link to="/auth" className="btn">
          Sign in
        </Link>
      </header>

      <section className="mx-auto max-w-6xl px-5 pt-20 pb-16">
        <p className="microcaps">Athlete monetization, measured</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold leading-tight tracking-tight text-mist-100 md:text-5xl">
          Where athletes, sponsors, and audiences meet on <span className="wave-text">evidence</span>.
        </h1>
        <p className="mt-5 max-w-2xl text-base text-mist-300">
          Stride turns connected social platforms into transparent marketability analytics, matches
          athletes to sponsorship campaigns with explainable scoring, and runs the deal flow end to end.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link to="/auth?mode=register" className="btn-primary">
            Create an account <ArrowRight size={15} />
          </Link>
          <Link to="/athletes" className="btn">
            Browse the athlete directory
          </Link>
        </div>
        <div className="mt-4 text-xs text-mist-400">
          Four account types — athlete, club, sponsor, supporter. Demo credentials in the sign-in screen.
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-5 pb-24 md:grid-cols-3">
        {PILLARS.map(({ icon: Icon, title, body }) => (
          <div key={title} className="panel p-6">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-ink-800">
              <Icon size={17} strokeWidth={1.8} className="text-pulse-400" />
            </div>
            <h3 className="mt-4 font-medium text-mist-100">{title}</h3>
            <p className="mt-2 text-sm text-mist-300">{body}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-line py-6 text-center text-xs text-mist-400">
        Stride — first product draft. Simulated athlete and sponsor data for evaluation.
      </footer>
    </div>
  )
}
