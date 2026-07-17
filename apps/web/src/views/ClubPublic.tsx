import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Avatar, EmptyNote, Section } from '../components/ui'
import { api, errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { fmtMoney } from '../lib/format'
import type { Club, ClubPackage, RosterMember } from '../types'

interface ClubDetail extends Club {
  roster: RosterMember[]
  packages: ClubPackage[]
}

export default function ClubPublic() {
  const { slug } = useParams()
  const { me } = useAuth()
  const [club, setClub] = useState<ClubDetail | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = () =>
    api.get<ClubDetail>(`/api/clubs/${slug}`).then(setClub).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [slug])

  const back = async (p: ClubPackage) => {
    setError('')
    setNotice('')
    try {
      await api.post(`/api/clubs/packages/${p.id}/commit`)
      setNotice(`You are now backing "${p.name}" — track it in your pipeline.`)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!club) return <div className="text-mist-400">{error || 'Loading club…'}</div>

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4">
        <Avatar name={club.name} size={56} />
        <div>
          <h1 className="text-2xl font-semibold text-mist-100">{club.name}</h1>
          <div className="text-sm text-mist-400">{club.sport} · {club.country} · {club.region}</div>
        </div>
        <div className="ml-auto flex gap-2">
          <span className="chip">{club.backer_count} active backers</span>
        </div>
      </div>
      {club.bio && <p className="mt-4 max-w-2xl text-sm text-mist-300">{club.bio}</p>}
      {notice && <div className="mt-4 rounded-lg border border-ok/40 bg-ok/10 px-3 py-2 text-sm text-ok">{notice}</div>}
      {error && <div className="mt-4 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}

      <Section title="Sponsorship packages">
        {club.packages.length === 0 && <EmptyNote text="No active packages." />}
        <div className="grid gap-3 md:grid-cols-2">
          {club.packages.map((p) => (
            <div key={p.id} className="panel p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-mist-100">{p.name}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <span className={`chip ${p.package_type === 'player_direct' ? 'border-pulse-500 text-mist-100' : ''}`}>
                      {p.package_type === 'player_direct' ? 'Player-direct' : 'Club package'}
                    </span>
                    {p.athlete_slug && (
                      <Link to={`/athletes/${p.athlete_slug}`} className="chip hover:border-pulse-500">
                        {p.athlete_name}
                      </Link>
                    )}
                  </div>
                </div>
                <div className="tnum text-lg font-semibold text-mist-100">{fmtMoney(p.price_usd)}</div>
              </div>
              {p.description && <p className="mt-2 text-sm text-mist-300">{p.description}</p>}
              {p.perks.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-xs text-mist-400">
                  {p.perks.map((perk) => <li key={perk}>· {perk}</li>)}
                </ul>
              )}
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-mist-400">{p.active_backers} active backer{p.active_backers === 1 ? '' : 's'}</span>
                {me?.role === 'sponsor' && (
                  <button className="btn-primary px-3 py-1.5 text-xs" onClick={() => back(p)}>
                    Back this package
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
        {me?.role !== 'sponsor' && (
          <p className="mt-3 text-xs text-mist-400">Sponsors can back packages from their account.</p>
        )}
      </Section>

      <Section title={`Roster (${club.roster.length})`}>
        <div className="grid gap-2 md:grid-cols-2">
          {club.roster.map((m) => (
            <Link key={m.athlete_id} to={`/athletes/${m.slug}`} className="panel panel-hover flex items-center gap-3 p-3">
              <Avatar name={m.display_name} size={36} />
              <div>
                <div className="text-sm font-medium text-mist-100">{m.display_name}</div>
                <div className="text-xs text-mist-400">{m.position || m.sport} · {m.country}</div>
              </div>
            </Link>
          ))}
        </div>
      </Section>
    </div>
  )
}
