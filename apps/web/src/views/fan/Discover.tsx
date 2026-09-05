import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, CoverageChip, EmptyNote, LoadError, MessageButton, PageHeader, PageLoading } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import type { AthletePublic, Club, Facets } from '../../types'

// Kept only as the order to show first; the live list comes from the facets so
// a sport nobody has yet does not appear, and a new one does not need a deploy.
const INTEREST_ORDER = ['Athletics', 'Football', 'Basketball', 'Tennis', 'Cycling', 'Swimming', 'Boxing', 'MMA',
  'Surfing', 'Climbing', 'Golf', 'fitness', 'endurance', 'travel', 'wellness', 'lifestyle']

/** Module scope, not inside `Discover`: a component declared in a render body is
 *  a new type each time, so every state change remounted every card and dropped
 *  focus from whichever Follow button was being used. */
function DiscoverCard({ a, rank, best = false, me, onFollow, onSubscribe }: {
  a: AthletePublic
  rank: number | null
  best?: boolean
  me: boolean
  onFollow: (a: AthletePublic) => void
  onSubscribe: (a: AthletePublic) => void
}) {
  return (
          <div
            className={`panel panel-hover p-4 ${
              best ? 'border-accent/70 bg-accent/[0.04]' : ''
            }`}
          >
            <div className="flex items-center gap-3">
              <Avatar name={a.display_name} size={42} />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Link to={`/athletes/${a.slug}`} className="font-medium text-ink hover:text-accent">
                    {a.display_name}
                  </Link>
                  {best && (
                    <span className="rounded-full bg-accent px-2 py-0.5 font-display text-[10px]
                                     font-bold uppercase tracking-board text-accent-on">
                      Best match
                    </span>
                  )}
                </div>
                <div className="text-xs text-ink-3">{a.sport} · {a.country}</div>
              </div>
              <div className="ml-auto flex items-center gap-2">
                {rank !== null && a.affinity != null && (
                  <span className="tnum font-display text-lg font-bold text-ink" title="Affinity score">
                    {Math.round(a.affinity)}
                  </span>
                )}
                {/* Coverage says how complete our analytics are. That is a
                    sponsor's question; it is absent from a fan's payload, so
                    the chip only appears when the score came with it. */}
                {a.score !== undefined && <CoverageChip coverage={a.score?.coverage ?? null} />}
                {a.can_message && <MessageButton to={{ athlete: a.slug }} name={a.display_name} />}
                {me && (
                  <>
                    <button className={`btn px-3 py-1 text-xs ${a.following ? 'border-accent text-ink' : ''}`}
                            onClick={() => onFollow(a)}>
                      {a.following ? 'Following' : 'Follow'}
                    </button>
                    <button className={a.subscribed
                              ? 'btn border-accent px-3 py-1 text-xs text-ink'
                              : 'btn-go px-3 py-1 text-xs'}
                            onClick={() => onSubscribe(a)}>
                      {a.subscribed ? 'Subscribed' : 'Subscribe'}
                    </button>
                  </>
                )}
              </div>
            </div>
            {(a.reasons?.length ?? 0) > 0 && (
              <ul className="mt-3 space-y-0.5 text-xs text-ink-3">
                {a.reasons!.map((r) => <li key={r}>· {r}</li>)}
              </ul>
            )}
          </div>
  )
}

export default function Discover() {
  const { me } = useAuth()
  const [selected, setSelected] = useState<string[]>([])
  const [country, setCountry] = useState('')
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [error, setError] = useState('')
  // The interests offered are the sports and themes that actually exist. The
  // constant above only decides what comes first — a hard-coded list would both
  // offer sports nobody competes in and hide the first athlete in a new one.
  const [clubs, setClubs] = useState<Club[]>([])
  const [q, setQ] = useState('')
  const [sport, setSport] = useState('')
  const [kind, setKind] = useState<'all' | 'athlete' | 'club'>('all')
  const [facets, setFacets] = useState<Facets | null>(null)
  const [facetsFailed, setFacetsFailed] = useState(false)
  useEffect(() => {
    api.get<Facets>('/api/athletes/facets')
      .then(setFacets)
      .catch(() => setFacetsFailed(true))
  }, [])
  const interests = useMemo(() => {
    // Sports and topics overlap — "Football" the sport and "football" the topic
    // are the same server-side interest, and rendering both gave two buttons
    // that did the same thing. First spelling seen wins.
    const seen = new Map<string, string>()
    for (const v of [...(facets?.sports ?? []), ...(facets?.topics ?? [])]) {
      if (!seen.has(v.toLowerCase())) seen.set(v.toLowerCase(), v)
    }
    const rank = (v: string) => {
      const i = INTEREST_ORDER.findIndex((o) => o.toLowerCase() === v.toLowerCase())
      return i === -1 ? INTEREST_ORDER.length : i
    }
    return [...seen.values()].sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
  }, [facets])

  const query = useMemo(() => {
    const p = new URLSearchParams()
    if (selected.length) p.set('interests', selected.join(','))
    if (country) p.set('country', country)
    if (q.trim()) p.set('q', q.trim())
    if (sport) p.set('sport', sport)
    if (kind !== 'all') p.set('kind', kind)
    return p.toString()
  }, [selected, country, q, sport, kind])

  useEffect(() => {
    setError('')
    api.get<{ athletes: AthletePublic[]; clubs: Club[] }>(`/api/discover?${query}`)
      .then((r) => { setAthletes(r.athletes); setClubs(r.clubs) })
      .catch((e) => setError(errorText(e)))
  }, [query])

  // mutation failures report in place; only a failed first load takes the page
  const firstLoadFailed = !athletes && error

  // Admin reaches this page (ops look at the ranking) but cannot follow: the
  // API allows athlete, fan and sponsor only. Showing the control to a role the
  // server will refuse produces a button whose entire behaviour is an error.
  const canFollow = !!me && ['athlete', 'fan', 'sponsor'].includes(me.role)

  const toggleFollow = async (a: AthletePublic) => {
    if (!canFollow) return
    try {
      if (a.following) await api.del(`/api/follows/${a.id}`)
      else await api.post(`/api/follows/${a.id}`)
      setAthletes((list) => list?.map((x) => (x.id === a.id ? { ...x, following: !a.following } : x)) ?? null)
    } catch (e) {
      setError(errorText(e))
    }
  }

  const toggleSubscribe = async (a: AthletePublic) => {
    if (!canFollow) return
    const path = `/api/subscriptions/athlete/${a.id}`
    try {
      if (a.subscribed) await api.del(path)
      else await api.post(path)
      setAthletes((list) => list?.map((x) => (x.id === a.id ? { ...x, subscribed: !a.subscribed } : x)) ?? null)
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (firstLoadFailed) return <LoadError text={error} />

  return (
    <div>
      <PageHeader
        eyebrow="Supporter"
        title="Discover athletes"
        lede="Pick your interests — the ranking explains every suggestion."
      />

      <div className="flex flex-wrap items-center gap-2">
        {facetsFailed && (
          <span className="meta text-critical">
            Interest filters could not be loaded — showing everything.
          </span>
        )}
        {interests.map((i: string) => (
          <button key={i}
                  onClick={() => setSelected((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]))}
                  className={`tag cursor-pointer ${selected.includes(i) ? 'border-accent text-ink' : ''}`}>
            {i}
          </button>
        ))}
      </div>

      {/* One search box and one set of filters, because clubs and athletes are
          both things a reader is looking for and splitting them into two
          directories meant asking the same question twice. */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input aria-label="Search athletes and clubs" className="field w-64 py-1.5 text-sm" placeholder="Search athletes and clubs"
               value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label="Filter by sport" className="field w-40 py-1.5 text-xs" value={sport}
                onChange={(e) => setSport(e.target.value)}>
          <option value="">All sports</option>
          {(facets?.sports ?? []).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select aria-label="Filter by country" className="field w-44 py-1.5 text-xs" value={country}
                onChange={(e) => setCountry(e.target.value)}>
          <option value="">All countries</option>
          {(facets?.countries ?? []).map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <div className="flex gap-1 rounded border border-line p-0.5">
          {(['all', 'athlete', 'club'] as const).map((k) => (
            <button key={k} onClick={() => setKind(k)}
                    className={`rounded px-3 py-1 font-display text-[11px] uppercase tracking-micro ${
                      kind === k ? 'bg-track text-ink' : 'text-ink-3 hover:text-ink-2'}`}>
              {k === 'all' ? 'Everyone' : k === 'athlete' ? 'Athletes' : 'Clubs'}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      {!athletes && <div className="mt-6"><PageLoading rows={2} /></div>}

      {/* The ranking already produced an order and a reason for it; rendering
          every card the same way threw that away. The top three are marked as
          recommended and the best of them carries the accent, so the list reads
          as ranked rather than merely sorted. */}
      {(() => {
        if (!athletes) return null
        const top = athletes.slice(0, 3)
        const rest = athletes.slice(3)
        // "Best match" is a claim about evidence, not about sort order. Equal
        // affinities break alphabetically, so crowning the first of three tied
        // athletes told a fan that Andre beat Kaia on merit when he beat her on
        // the letter A. Pick one interest — the commonest first move — and all
        // three carried the same score and the same single reason. Mark a winner
        // only when there is one; otherwise the three stand as equals, which is
        // what the ranking actually found.
        const clearWinner = top.length > 0 && top[0].affinity != null
          && (top.length === 1 || top[1].affinity == null || top[0].affinity > top[1].affinity)

        return (
          <>
            {top.length > 0 && (
              <>
                <div className="mt-6 flex items-baseline justify-between gap-3 border-b border-line pb-2">
                  <span className="cap">Recommended for you</span>
                  <span className="meta">ranked on your interests — every card says why</span>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {top.map((a, i) => (
                    <DiscoverCard key={a.id} a={a} rank={i} best={i === 0 && clearWinner}
                                  me={canFollow} onFollow={toggleFollow} onSubscribe={toggleSubscribe} />
                  ))}
                </div>
              </>
            )}
            {rest.length > 0 && (
              <>
                <div className="mt-8 border-b border-line pb-2">
                  <span className="cap">More athletes</span>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {rest.map((a) => (
                    <DiscoverCard key={a.id} a={a} rank={null} me={canFollow} onFollow={toggleFollow} onSubscribe={toggleSubscribe} />
                  ))}
                </div>
              </>
            )}
          </>
        )
      })()}
      {clubs.length > 0 && (
        <>
          <div className="mt-8 border-b border-line pb-2"><span className="cap">Clubs</span></div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {clubs.map((c) => (
              <Link key={c.slug} to={`/clubs/${c.slug}`}
                    className="panel panel-hover flex items-center gap-3 p-4">
                <Avatar name={c.name} size={42} />
                <div className="min-w-0">
                  <div className="font-medium text-ink">{c.name}</div>
                  <div className="text-xs text-ink-3">{c.sport} · {c.country}</div>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}

      {athletes && athletes.length === 0 && clubs.length === 0 && (
        <EmptyNote text="Nothing matches those filters yet." />
      )}
    </div>
  )
}
