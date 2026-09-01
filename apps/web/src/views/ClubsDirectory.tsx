import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { LoadError, PageHeader, PageLoading, Avatar, EmptyNote } from '../components/ui'
import { api, errorText } from '../lib/api'
import type { Club } from '../types'

export default function ClubsDirectory({ embedded = false }: { embedded?: boolean } = {}) {
  const [clubs, setClubs] = useState<Club[] | null>(null)
  const [q, setQ] = useState('')
  const [sport, setSport] = useState('')
  const [country, setCountry] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Club[]>('/api/clubs').then(setClubs).catch((e) => setError(errorText(e)))
  }, [])

  /** Filtered here rather than on the server: the club list is small and comes
   *  back whole, so a round trip per keystroke would be slower and no more
   *  correct. The options come from the clubs that exist, so a sport nobody
   *  competes in is never offered. */
  const sports = useMemo(
    () => [...new Set((clubs ?? []).map((c) => c.sport))].sort(), [clubs])
  const countries = useMemo(
    () => [...new Set((clubs ?? []).map((c) => c.country))].sort(), [clubs])
  const shown = useMemo(() => (clubs ?? []).filter((c) =>
    (!q.trim() || c.name.toLowerCase().includes(q.trim().toLowerCase()))
    && (!sport || c.sport === sport)
    && (!country || c.country === country)), [clubs, q, sport, country])

  if (!clubs) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      {!embedded && (
      <PageHeader
          eyebrow="Directory"
          title="Clubs"
          lede="Clubs manage rosters of Stride athletes and publish sponsorship packages — including player-direct packages that back an individual athlete through the club."
          aside={<span className="meta">
            {shown.length === clubs.length
              ? `${clubs.length} club${clubs.length === 1 ? '' : 's'}`
              : `${shown.length} of ${clubs.length}`}
          </span>}
        />
      )}


      {/* The same three questions the athlete directory and Discover ask.
          This list had none of them: it was the one directory you could only
          scroll. */}
      <div className="mb-5 flex flex-wrap items-center gap-2">
        <input className="field w-64 py-1.5 text-sm" placeholder="Search clubs"
               value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="field w-40 py-1.5 text-xs" value={sport}
                onChange={(e) => setSport(e.target.value)}>
          <option value="">All sports</option>
          {sports.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
        <select className="field w-44 py-1.5 text-xs" value={country}
                onChange={(e) => setCountry(e.target.value)}>
          <option value="">All countries</option>
          {countries.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {shown.map((c) => (
          <Link key={c.id} to={`/clubs/${c.slug}`} className="panel panel-hover block p-5">
            <div className="flex items-center gap-3">
              <Avatar name={c.name} size={44} />
              <div>
                <div className="font-medium text-ink">{c.name}</div>
                <div className="text-xs text-ink-3">{c.sport} · {c.country}</div>
              </div>
            </div>
            <p className="mt-3 text-sm text-ink-2 line-clamp-2">{c.bio}</p>
            <div className="mt-3 flex gap-2 text-xs">
              <span className="tag">{c.member_count} roster athletes</span>
              <span className="tag">{c.package_count} packages</span>
              <span className="tag">{c.backer_count} backers</span>
            </div>
          </Link>
        ))}
      </div>
      {shown.length === 0 && (
        <EmptyNote text={clubs.length === 0
          ? 'No clubs listed yet.'
          : 'No clubs match those filters.'} />
      )}
    </div>
  )
}
