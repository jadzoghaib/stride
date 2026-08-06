import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LoadError, PageLoading, Avatar, CoverageChip, EmptyNote, Sparkline } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import type { AthletePublic } from '../../types'

export default function Feed() {
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<AthletePublic[]>('/api/feed').then(setAthletes).catch((e) => setError(errorText(e)))
  }, [])

  if (!athletes) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink">Following</h1>
      <p className="mt-1 text-sm text-ink-3">Trajectory of the athletes you follow — audience scale over recent score snapshots.</p>

      {athletes.length === 0 ? (
        <div className="mt-6">
          <EmptyNote text="You are not following anyone yet." action={<Link className="btn-go" to="/discover">Discover athletes</Link>} />
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {athletes.map((a) => (
            <div key={a.id} className="panel panel-hover flex items-center gap-4 p-4">
              <Avatar name={a.display_name} size={42} />
              <div className="min-w-0">
                <Link to={`/athletes/${a.slug}`} className="font-medium text-ink hover:text-accent">
                  {a.display_name}
                </Link>
                <div className="text-xs text-ink-3">{a.sport} · {a.country}</div>
              </div>
              <div className="ml-auto flex items-center gap-5">
                <Sparkline points={(a.score_history ?? []).map((h) => h.audience_scale ?? 0)} />
                <CoverageChip coverage={a.score?.coverage ?? null} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
