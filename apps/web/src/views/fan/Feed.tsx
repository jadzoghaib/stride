import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ContentList } from '../../components/content'
import { LoadError, PageHeader, PageLoading, Avatar, CoverageChip, EmptyNote, Sparkline } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import type { AthletePublic, ContentItem } from '../../types'

export default function Feed() {
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [posts, setPosts] = useState<ContentItem[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<AthletePublic[]>('/api/feed').then(setAthletes).catch((e) => setError(errorText(e)))
    // The free layer, and the reason a fan opens the app between paid drops.
    // Its own failure: losing the posts must not cost the reader the trajectory
    // panel underneath, which is the part that is always there.
    api.get<ContentItem[]>('/api/feed/content').then(setPosts).catch(() => setPosts([]))
  }, [])

  if (!athletes) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      <PageHeader
        eyebrow="Supporter"
        title="Following"
        lede="What the athletes you follow have published, and how their audience is moving."
        aside={<span className="meta">{athletes.length} followed</span>}
      />

      {athletes.length > 0 && posts && posts.length > 0 && (
        <div className="mb-8">
          <div className="mb-3 flex items-baseline justify-between gap-3 border-b border-line pb-2">
            <span className="cap">Latest</span>
            <span className="meta">newest first · locked items show what they would take</span>
          </div>
          <ContentList items={posts} showAuthor empty="Nothing published yet." />
        </div>
      )}

      {athletes.length > 0 && (
        <div className="mb-3 border-b border-line pb-2"><span className="cap">Trajectory</span></div>
      )}

      {athletes.length === 0 ? (
        <div>
          <EmptyNote text="You are not following anyone yet." action={<Link className="btn-go" to="/discover">Discover athletes</Link>} />
        </div>
      ) : (
        <div className="space-y-3">
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
