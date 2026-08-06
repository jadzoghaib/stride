import { ArrowRight } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import { ThemeToggle, Wordmark } from '../components/Shell'
import { Meter } from '../components/ui'
import { roleHome, useAuth } from '../lib/auth'

/** The hero is the product's own artifact: the dimension rack an athlete
 *  actually sees. Marked illustrative, because these are not a real athlete's
 *  numbers and the whole pitch is that the numbers are traceable. */
const SAMPLE = [
  { label: 'Audience Scale', value: 91 },
  { label: 'Audience Fit', value: 88 },
  { label: 'Engagement Quality', value: 77 },
  { label: 'Consistency', value: 74 },
  { label: 'Growth', value: 62 },
]

const PILLARS = [
  {
    title: 'Evidence, not estimates',
    body: 'Marketability is computed from connected social platforms through a versioned formula set — audience scale, engagement quality, fit, growth, consistency. Every score can be traced to the posts and snapshots behind it.',
  },
  {
    title: 'Matching that explains itself',
    body: 'Sponsors rank athletes against a specific campaign brief. Each match shows its component breakdown — audience fit against your target, budget alignment, format overlap — with plain-language reasons and caveats.',
  },
  {
    title: 'A governed marketplace',
    body: 'Offers, acceptances, and every account action land in an audit trail. Partial data is labeled, never hidden: an athlete with one connected platform is scored on one platform.',
  },
]

export default function Landing() {
  const { me, loading } = useAuth()
  if (!loading && me) return <Navigate to={roleHome(me.role)} replace />

  return (
    <div className="min-h-screen bg-ground">
      <header className="mx-auto flex h-16 max-w-[1140px] items-center justify-between px-7">
        <Wordmark size="text-[24px]" />
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Link to="/auth" className="btn">
            Sign in
          </Link>
        </div>
      </header>

      <section className="board" style={{ ['--board-rule' as string]: '78%' }}>
        <div className="relative mx-auto grid max-w-[1140px] items-center gap-14 px-7 pb-20 pt-16 lg:grid-cols-[1.05fr_.95fr]">
          <div>
            <p className="cap">Athlete monetization, measured</p>
            <h1 className="mt-5 text-[clamp(40px,5.2vw,68px)] leading-[.98] tracking-board">
              Where athletes, sponsors, and audiences meet on <span className="text-accent-ink">evidence</span>.
            </h1>
            <p className="mt-6 max-w-xl text-ink-2">
              Stride turns connected social platforms into transparent marketability analytics, matches athletes to
              sponsorship campaigns with explainable scoring, and runs the deal flow end to end.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              <Link to="/auth?mode=register" className="btn-go">
                Create an account <ArrowRight size={15} />
              </Link>
              <Link to="/athletes" className="btn">
                Browse the athlete directory
              </Link>
            </div>
            <p className="meta mt-5">
              Four account types — athlete, club, sponsor, supporter. Demo credentials on the sign-in screen.
            </p>
          </div>

          <div className="panel overflow-hidden">
            <div className="flex items-baseline justify-between border-b border-line px-4 py-3">
              <span className="cap">Marketability</span>
              <span className="meta">illustrative</span>
            </div>
            {SAMPLE.map((d, i) => (
              <div key={d.label} className="grid grid-cols-[28px_1fr_54px] items-center gap-3 border-b border-line px-4 py-3 last:border-b-0">
                <span className="font-display text-xl font-bold leading-none text-ink-3 tnum">{i + 1}</span>
                <div>
                  <div className="font-display text-[13px] font-semibold uppercase tracking-board text-ink">{d.label}</div>
                  <div className="mt-1.5">
                    <Meter value={d.value} delay={i * 85} muted={d.value < 65} />
                  </div>
                </div>
                <span className="text-right font-display text-xl font-bold text-ink tnum">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-[1140px] gap-5 px-7 py-16 md:grid-cols-3">
        {PILLARS.map(({ title, body }) => (
          <div key={title} className="panel p-6">
            <h3 className="text-lg tracking-board">{title}</h3>
            <p className="mt-3 text-sm text-ink-2">{body}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-line py-7 text-center">
        <p className="meta">Stride — first product draft. Simulated athlete and sponsor data for evaluation.</p>
      </footer>
    </div>
  )
}
