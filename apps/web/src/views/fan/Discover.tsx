import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, CoverageChip, EmptyNote, LoadError, PageHeader, PageLoading } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import type { AthletePublic, Facets } from '../../types'

// Kept only as the order to show first; the live list comes from the facets so
// a sport nobody has yet does not appear, and a new one does not need a deploy.
const INTEREST_ORDER = ['Athletics', 'Football', 'Basketball', 'Tennis', 'Cycling', 'Swimming', 'Boxing', 'MMA',
  'Surfing', 'Climbing', 'Golf', 'fitness', 'endurance', 'travel', 'wellness', 'lifestyle']

export default function Discover() {
  const { me } = useAuth()
  const [selected, setSelected] = useState<string[]>([])
  const [country, setCountry] = useState('')
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [error, setError] = useState('')
  // The interests offered are the sports and themes that actually exist. The
  // constant above only decides what comes first — a hard-coded list would both
  // offer sports nobody competes in and hide the first athlete in a new one.
  const [facets, setFacets] = useState<Facets | null>(null)
  useEffect(() => {
    api.get<Facets>('/api/athletes/facets').then(setFacets).catch(() => {})
  }, [])
  const interests = useMemo(() => {
    const live = [...(facets?.sports ?? []), ...(facets?.topics ?? [])]
    const rank = (v: string) => {
      const i = INTEREST_ORDER.findIndex((o) => o.toLowerCase() === v.toLowerCase())
      return i === -1 ? INTEREST_ORDER.length : i
    }
    return live.sort((a, b) => rank(a) - rank(b) || a.localeCompare(b))
  }, [facets])

  const query = useMemo(() => {
    const p = new URLSearchParams()
    if (selected.length) p.set('interests', selected.join(','))
    if (country) p.set('country', country)
    return p.toString()
  }, [selected, country])

  useEffect(() => {
    setError('')
    api.get<AthletePublic[]>(`/api/discover?${query}`).then(setAthletes).catch((e) => setError(errorText(e)))
  }, [query])

  // mutation failures report in place; only a failed first load takes the page
  const firstLoadFailed = !athletes && error

  const toggleFollow = async (a: AthletePublic) => {
    if (!me) return
    try {
      if (a.following) await api.del(`/api/follows/${a.id}`)
      else await api.post(`/api/follows/${a.id}`)
      setAthletes((list) => list?.map((x) => (x.id === a.id ? { ...x, following: !a.following } : x)) ?? null)
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
        {interests.map((i: string) => (
          <button key={i}
                  onClick={() => setSelected((s) => (s.includes(i) ? s.filter((x) => x !== i) : [...s, i]))}
                  className={`tag cursor-pointer ${selected.includes(i) ? 'border-accent text-ink' : ''}`}>
            {i}
          </button>
        ))}
        <input className="field w-44 py-1 text-xs" placeholder="Your country (optional)"
               value={country} onChange={(e) => setCountry(e.target.value)} />
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

        const Card = ({ a, rank }: { a: (typeof athletes)[number]; rank: number | null }) => (
          <div
            className={`panel panel-hover p-4 ${
              rank === 0 ? 'border-accent/70 bg-accent/[0.04]' : ''
            }`}
          >
            <div className="flex items-center gap-3">
              <Avatar name={a.display_name} size={42} />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Link to={`/athletes/${a.slug}`} className="font-medium text-ink hover:text-accent">
                    {a.display_name}
                  </Link>
                  {rank === 0 && (
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
                <CoverageChip coverage={a.score?.coverage ?? null} />
                {me && (
                  <button className={`btn px-3 py-1 text-xs ${a.following ? 'border-accent text-ink' : ''}`}
                          onClick={() => toggleFollow(a)}>
                    {a.following ? 'Following' : 'Follow'}
                  </button>
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

        return (
          <>
            {top.length > 0 && (
              <>
                <div className="mt-6 flex items-baseline justify-between gap-3 border-b border-line pb-2">
                  <span className="cap">Recommended for you</span>
                  <span className="meta">ranked on your interests — every card says why</span>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {top.map((a, i) => <Card key={a.id} a={a} rank={i} />)}
                </div>
              </>
            )}
            {rest.length > 0 && (
              <>
                <div className="mt-8 border-b border-line pb-2">
                  <span className="cap">More athletes</span>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  {rest.map((a) => <Card key={a.id} a={a} rank={null} />)}
                </div>
              </>
            )}
          </>
        )
      })()}
      {athletes && athletes.length === 0 && <EmptyNote text="No athletes match those filters yet." />}
    </div>
  )
}
