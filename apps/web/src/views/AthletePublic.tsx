import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Board } from '../components/Board'
import { AudiencePanel } from '../components/charts'
import { ContentTabs } from '../components/content'
import { LoadError, PageLoading, CoverageChip, DimensionGrid, Section } from '../components/ui'
import { api, errorText } from '../lib/api'
import { fmtMoney } from '../lib/format'
import type { AthletePublic as Athlete, ContentItem, NewsItem } from '../types'
import { dealTypeLabel, meanScore } from '../types'

export default function AthletePublicView() {
  const { slug } = useParams()
  const [a, setA] = useState<Athlete | null>(null)
  const [content, setContent] = useState<ContentItem[] | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
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
          { label: 'Rate card', value: fmtMoney(a.base_rate_eur) },
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

      {a.career_highlights.length > 0 && (
        <Section title="Career highlights">
          <ul className="space-y-1 text-sm text-ink-2">
            {a.career_highlights.map((h) => <li key={h} className="flex gap-2"><span className="text-accent">—</span>{h}</li>)}
          </ul>
        </Section>
      )}

      <Section title="Marketability">
        <DimensionGrid score={a.score} />
      </Section>

      {a.audience && Object.keys(a.audience).length > 0 && (
        <Section title="Audience">
          <AudiencePanel audience={a.audience} />
        </Section>
      )}

      {content && (content.length > 0 || news.length > 0) && (
        <Section title="From this athlete">
          <ContentTabs items={content} news={news} />
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
