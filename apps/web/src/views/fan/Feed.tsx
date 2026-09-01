import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ContentCard, Wall } from '../../components/content'
import { LoadError, PageHeader, PageLoading, Avatar, CoverageChip, EmptyNote, Sparkline } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import type { AthletePublic, ContentItem, NewsItem } from '../../types'

export default function Feed() {
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [posts, setPosts] = useState<ContentItem[] | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<AthletePublic[]>('/api/feed').then(setAthletes).catch((e) => setError(errorText(e)))
    // The free layer, and the reason a fan opens the app between paid drops.
    // Its own failure: losing the posts must not cost the reader the trajectory
    // panel underneath, which is the part that is always there.
    api.get<ContentItem[]>('/api/feed/content').then(setPosts).catch(() => setPosts([]))
    // Following buys the free tier, and an athlete's public platform posts are
    // most of what that is. Without them a fan following four athletes saw only
    // what those four had published *inside* Stride — on young profiles, close
    // to nothing, so the tier meant to keep them was empty.
    api.get<NewsItem[]>('/api/feed/news').then(setNews).catch(() => setNews([]))
  }, [])

  if (!athletes) return error ? <LoadError text={error} /> : <PageLoading />

  const now = Date.now()
  const items = posts ?? []
  const upcoming = items
    .filter((i) => i.starts_at && new Date(i.starts_at).getTime() > now)
    .sort((a, b) => +new Date(a.starts_at as string) - +new Date(b.starts_at as string))
  const wallPosts = items.filter((i) => i.kind === 'post' && !i.part_of)

  return (
    <div>
      <PageHeader
        eyebrow="Supporter"
        title="Following"
        lede="What the athletes you follow have published, and how their audience is moving."
        aside={<span className="meta">{athletes.length} followed</span>}
      />

      {/* A feed is a stream, but the one thing in it with a deadline should
          not have to be scrolled to. Anything bookable and still to come sits
          above the wall; everything else is the wall, newest first. */}
      {athletes.length > 0 && upcoming.length > 0 && (
        <div className="mb-8">
          <div className="mb-3 flex items-baseline justify-between gap-3 border-b border-line pb-2">
            <span className="cap text-accent-ink">Coming up</span>
            <span className="meta">from the athletes you follow</span>
          </div>
          <div className="space-y-2">
            {upcoming.map((i) => <ContentCard key={i.id} item={i} showAuthor />)}
          </div>
        </div>
      )}

      {athletes.length > 0 && (wallPosts.length > 0 || news.length > 0) && (
        <div className="mb-8">
          <div className="mb-3 flex items-baseline justify-between gap-3 border-b border-line pb-2">
            <span className="cap">Wall</span>
            <span className="meta">newest first · locked items show what they would take</span>
          </div>
          <Wall items={wallPosts} news={news} showAuthor empty="Nothing published yet." />
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
