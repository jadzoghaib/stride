import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, CoverageChip, EmptyNote, LoadError, PageHeader, PageLoading } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import type { AthletePublic } from '../../types'

const INTERESTS = ['Athletics', 'Football', 'Basketball', 'Tennis', 'Cycling', 'Swimming', 'Boxing', 'MMA',
  'Surfing', 'Climbing', 'Golf', 'fitness', 'endurance', 'travel', 'wellness', 'lifestyle']

export default function Discover() {
  const { me } = useAuth()
  const [selected, setSelected] = useState<string[]>([])
  const [country, setCountry] = useState('')
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [error, setError] = useState('')

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
        {INTERESTS.map((i) => (
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

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {athletes?.map((a) => (
          <div key={a.id} className="panel panel-hover p-4">
            <div className="flex items-center gap-3">
              <Avatar name={a.display_name} size={42} />
              <div className="min-w-0">
                <Link to={`/athletes/${a.slug}`} className="font-medium text-ink hover:text-accent">
                  {a.display_name}
                </Link>
                <div className="text-xs text-ink-3">{a.sport} · {a.country}</div>
              </div>
              <div className="ml-auto flex items-center gap-2">
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
        ))}
      </div>
      {athletes && athletes.length === 0 && <EmptyNote text="No athletes match those filters yet." />}
    </div>
  )
}
