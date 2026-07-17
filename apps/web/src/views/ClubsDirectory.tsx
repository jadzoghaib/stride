import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, EmptyNote } from '../components/ui'
import { api, errorText } from '../lib/api'
import type { Club } from '../types'

export default function ClubsDirectory() {
  const [clubs, setClubs] = useState<Club[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Club[]>('/api/clubs').then(setClubs).catch((e) => setError(errorText(e)))
  }, [])

  if (!clubs) return <div className="text-mist-400">{error || 'Loading clubs…'}</div>

  return (
    <div>
      <h1 className="text-2xl font-semibold text-mist-100">Clubs</h1>
      <p className="mt-1 text-sm text-mist-400">
        Clubs manage rosters of Stride athletes and publish sponsorship packages —
        including player-direct packages that back an individual athlete through the club.
      </p>
      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {clubs.map((c) => (
          <Link key={c.id} to={`/clubs/${c.slug}`} className="panel panel-hover block p-5">
            <div className="flex items-center gap-3">
              <Avatar name={c.name} size={44} />
              <div>
                <div className="font-medium text-mist-100">{c.name}</div>
                <div className="text-xs text-mist-400">{c.sport} · {c.country}</div>
              </div>
            </div>
            <p className="mt-3 text-sm text-mist-300 line-clamp-2">{c.bio}</p>
            <div className="mt-3 flex gap-2 text-xs">
              <span className="chip">{c.member_count} roster athletes</span>
              <span className="chip">{c.package_count} packages</span>
              <span className="chip">{c.backer_count} backers</span>
            </div>
          </Link>
        ))}
      </div>
      {clubs.length === 0 && <EmptyNote text="No clubs listed yet." />}
    </div>
  )
}
