import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Board } from '../components/Board'
import { AudiencePanel } from '../components/charts'
import { ContentTabs } from '../components/content'
import { LoadError, PageLoading, CoverageChip, DimensionGrid, MessageButton, Section } from '../components/ui'
import { api, errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { fmtMoney } from '../lib/format'
import type { AthletePublic as Athlete, ContentItem, NewsItem } from '../types'
import { dealTypeLabel, meanScore } from '../types'

export default function AthletePublicView() {
  const { slug } = useParams()
  const [a, setA] = useState<Athlete | null>(null)
  const [content, setContent] = useState<ContentItem[] | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const { me } = useAuth()
  // Follow and subscribe are two different relationships, so they are two
  // controls. Only the roles the API will accept get to see them.
  const canRelate = !!me && ['athlete', 'fan', 'sponsor'].includes(me.role)
  const vote = async (item: ContentItem, optionId: number) => {
    try {
      const poll = await api.post<ContentItem['poll']>(`/api/content/${item.id}/vote/${optionId}`)
      setContent((list) => list?.map((c) => (c.id === item.id ? { ...c, poll } : c)) ?? null)
    } catch (e) { setError(errorText(e)) }
  }

  const relate = async (kind: 'follow' | 'subscribe', on: boolean) => {
    if (!a) return
    const path = kind === 'follow' ? `/api/follows/${a.id}` : `/api/subscriptions/athlete/${a.id}`
    try {
      await (on ? api.del(path) : api.post(path))
      setA((prev) => prev && { ...prev, [kind === 'follow' ? 'following' : 'subscribed']: !on })
    } catch (e) { setError(errorText(e)) }
  }
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Athlete>(`/api/athletes/${slug}`).then(setA).catch((e) => setError(errorText(e)))
    // Its own request and its own failure: an athlete who has published nothing
    // is the common case, and a content error must not blank out the profile.
    api.get<ContentItem[]>(`/api/athletes/${slug}/content`).then(setContent).catch(() => setContent([]))
    // The wall is not empty just because nothing has been published here yet.
    api.get<NewsItem[]>(`/api/athletes/${slug}/news`).then(setNews).catch(() => setNews([]))
  }, [slug])

  if (!a) return error ? <LoadError text={error} /> : <PageLoading />

  const { value: overall, n: computedDims } = meanScore(a.score?.dimensions)
  const history = (a.score_history ?? [])
    .map((h) => h.audience_scale)
    .filter((v): v is number => typeof v === 'number')

  return (
    <>
      <Board
        eyebrow="Athlete"
        title={a.display_name}
        tags={
          <>
            <span className="tag">{a.sport}</span>
            <span className="tag">{a.country}</span>
            <CoverageChip coverage={a.score?.coverage ?? null} />
            {(a.clubs ?? []).map((c) => (
              <Link
                key={c.slug}
                to={`/clubs/${c.slug}`}
                className="tag border-accent/50 text-ink transition-colors hover:bg-raised"
                title={c.position ? `${c.position} — view club` : 'View club'}
              >
                {c.name}
              </Link>
            ))}
          </>
        }
        score={overall === null ? null : Math.round(overall)}
        scoreLabel="Marketability"
        deltaNote={
          computedDims
            ? `mean of ${computedDims} computed dimension${computedDims === 1 ? '' : 's'}`
            : 'not yet computed'
        }
        trend={history}
        trendLabel={history.length > 1 ? `audience scale · last ${history.length} snapshots` : undefined}
        figures={[
          // The rate card is a sponsorship asking price. It is absent from the
          // payload entirely for a fan, so this row simply is not there.
          ...(a.base_rate_eur === undefined
            ? []
            : [{ label: 'Rate card', value: fmtMoney(a.base_rate_eur) }]),
          { label: 'Region', value: a.region },
          {
            label: 'Club',
            value: (a.clubs ?? []).length ? (a.clubs ?? []).map((c) => c.name).join(', ') : 'Independent',
          },
        ]}
        footNote={a.score ? `computed ${a.score.computed_at.slice(0, 10)}` : undefined}
      />

      <div>
      {a.bio && <p className="mt-6 max-w-2xl text-sm text-ink-2">{a.bio}</p>}

      {(canRelate || a.socials.length > 0) && (
        <div className="mt-5 flex flex-wrap items-center gap-2">
          {canRelate && (
            <>
              <button className={`btn ${a.following ? 'border-accent text-ink' : ''}`}
                      onClick={() => relate('follow', !!a.following)}>
                {a.following ? 'Following' : 'Follow'}
              </button>
              <button className={a.subscribed ? 'btn border-accent text-ink' : 'btn-go'}
                      onClick={() => relate('subscribe', !!a.subscribed)}>
                {a.subscribed ? 'Subscribed' : 'Subscribe'}
              </button>
              {a.can_message && <MessageButton to={{ athlete: a.slug }} name={a.display_name} />}
              <span className="meta">
                Follow for their posts and platform news. Subscribe to open the
                subscribers-only ones.
              </span>
            </>
          )}
          {a.socials.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 md:ml-auto">
              {a.socials.map((s) => (
                <a key={s.platform} href={s.url} target="_blank" rel="noreferrer noopener"
                   className="tag hover:text-accent">
                  {s.platform}
                </a>
              ))}
            </div>
          )}
        </div>
      )}

      {a.career_highlights.length > 0 && (
        <Section title="Career highlights">
          <ul className="space-y-1 text-sm text-ink-2">
            {a.career_highlights.map((h) => <li key={h} className="flex gap-2"><span className="text-accent">—</span>{h}</li>)}
          </ul>
        </Section>
      )}

      {/* Marketability and the audience breakdown are the sponsor's evidence.
          The API omits both for a fan, so these sections disappear rather than
          render an empty shell. */}
      {a.score !== undefined && (
        <Section title="Marketability">
          <DimensionGrid score={a.score} />
        </Section>
      )}

      {a.audience && Object.keys(a.audience).length > 0 && (
        <Section title="Audience">
          <AudiencePanel audience={a.audience} />
        </Section>
      )}

      {content && (content.length > 0 || news.length > 0) && (
        <Section title="From this athlete">
          <ContentTabs items={content} news={news} onVote={vote} />
        </Section>
      )}

      <Section title="Open to">
        <div className="flex flex-wrap gap-2">
          {a.deal_types.map((t) => <span key={t} className="tag">{dealTypeLabel(t)}</span>)}
          {a.topics.map((t) => <span key={t} className="tag text-ink-3">{t}</span>)}
        </div>
      </Section>
      </div>
    </>
  )
}
