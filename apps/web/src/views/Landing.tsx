import { ArrowRight } from 'lucide-react'
import { Link, Navigate } from 'react-router-dom'
import Footer from '../components/Footer'
import { useState } from 'react'
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

const AUDIENCES = [
  { key: 'athlete', label: 'I compete',
    lede: 'A page that shows sponsors what your audience is actually worth — measured from the platforms you already post on, traceable to the posts behind it — and a way to be paid by the people who already follow you.',
    cta: 'Create your page', href: '/auth?mode=register&role=athlete' },
  { key: 'sponsor', label: 'I sponsor',
    lede: 'Brief a campaign and get athletes ranked against it, with the reasoning shown: audience fit against your target, budget alignment, format overlap. Then run the offer, the deliverables and the measurement in one place.',
    cta: 'Brief a campaign', href: '/auth?mode=register&role=sponsor' },
  { key: 'club', label: 'I run a club',
    lede: 'Put your roster in front of sponsors as a club, back individual players through the club, and vouch for athletes so they clear admission faster. The club is checked once; every player benefits.',
    cta: 'Register the club', href: '/auth?mode=register&role=club' },
  { key: 'fan', label: 'I follow',
    lede: 'Follow athletes for free and see what they publish and how they are moving. Subscribe to the ones you want more from — training blocks, sessions, the posts that never go on Instagram.',
    cta: 'Find athletes', href: '/discover' },
] as const
type Audience = (typeof AUDIENCES)[number]

export default function Landing() {
  const [who, setWho] = useState<Audience>(AUDIENCES[0])
  const { me, loading } = useAuth()
  if (!loading && me) return <Navigate to={roleHome(me.role)} replace />

  return (
    <div className="min-h-screen bg-ground">
      <header className="mx-auto flex h-16 max-w-page items-center justify-between px-7">
        <Wordmark size="text-brand" />
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <Link to="/auth" className="btn">
            Sign in
          </Link>
        </div>
      </header>

      <section className="board" style={{ ['--board-rule' as string]: '78%' }}>
        <div className="relative mx-auto grid max-w-page items-center gap-14 px-7 pb-20 pt-16 lg:grid-cols-[1.05fr_.95fr]">
          <div>
            <p className="cap">Athlete monetization, measured</p>
            <h1 className="mt-5 text-[clamp(40px,5.2vw,68px)] leading-[.98] tracking-board">
              Where athletes, sponsors, and audiences meet on <span className="text-accent-ink">evidence</span>.
            </h1>
            {/* One headline, four readers. The sentence under it used to be the
                pitch to a sponsor's analyst -- "versioned formula set",
                "explainable scoring" -- a real audience, and not the one that
                has to sign up first. Each reader gets the sentence that is
                about them and the button that starts their own path. */}
            <div className="mt-7 flex flex-wrap gap-1.5" role="tablist" aria-label="Who are you?">
              {AUDIENCES.map((a) => (
                <button key={a.key} type="button" role="tab" aria-selected={who.key === a.key}
                        onClick={() => setWho(a)}
                        className={`tag transition-colors ${who.key === a.key ? 'tag-accent' : 'hover:border-ink-3 hover:text-ink'}`}>
                  {a.label}
                </button>
              ))}
            </div>
            <p className="mt-4 max-w-xl text-ink-2" aria-live="polite">{who.lede}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link to={who.href} className="btn-go">
                {who.cta} <ArrowRight size={15} />
              </Link>
              <Link to="/athletes" className="btn">
                Browse the athlete directory
              </Link>
            </div>
            <p className="meta mt-5">
              Demo build — simulated data, shared credentials on the sign-in screen.
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
                  <div className="font-display text-small font-semibold uppercase tracking-board text-ink">{d.label}</div>
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

      <section className="mx-auto grid max-w-page gap-5 px-7 py-16 md:grid-cols-3">
        {PILLARS.map(({ title, body }) => (
          <div key={title} className="panel p-6">
            <h3 className="text-lg tracking-board">{title}</h3>
            <p className="mt-3 text-sm text-ink-2">{body}</p>
          </div>
        ))}
      </section>

      <div className="mx-auto max-w-page px-7">
        <p className="meta border-t border-line py-6 text-center">
          Stride — first product draft. Simulated athlete and sponsor data for evaluation.
        </p>
      </div>
      <Footer />
    </div>
  )
}
