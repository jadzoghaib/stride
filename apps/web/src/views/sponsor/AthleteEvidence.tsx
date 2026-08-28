import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Board } from '../../components/Board'
import { AudiencePanel } from '../../components/charts'
import { LoadError, PageLoading, CoverageChip, DimensionGrid, EmptyNote, Section } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney, fmtNum, fmtPct } from '../../lib/format'
import type { AthletePublic } from '../../types'
import { meanScore, platformLabel } from '../../types'

interface Evidence {
  athlete: AthletePublic
  analytics: {
    dimensions: Record<string, number | null>
    coverage: { platforms: { connected: number; total: number; list: string[]; missing: string[] } }
    inputs: { platform_kpis: Record<string, Record<string, number | null>> }
  } | null
  analytics_unavailable?: string
  audience: Record<string, Record<string, number>>
  posts: { platform: string; title: string; published_at: string; reach: number; engagement_rate: number | null }[]
}

export default function AthleteEvidence() {
  const { slug } = useParams()
  const [params] = useSearchParams()
  const campaignId = params.get('campaign')
  const [data, setData] = useState<Evidence | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const q = campaignId ? `?campaign_id=${campaignId}` : ''
    api.get<Evidence>(`/api/sponsor/athletes/${slug}/analytics${q}`).then(setData).catch((e) => setError(errorText(e)))
  }, [slug, campaignId])

  if (!data) return error ? <LoadError text={error} /> : <PageLoading />

  const a = data.athlete
  const kpis = data.analytics?.inputs.platform_kpis ?? {}

  // The live figure, not the stored snapshot: with a campaign in scope these
  // dimensions were recomputed against that campaign's own target, so the mean
  // is what this sponsor is actually looking at.
  const { value: overall, n: computedDims } = meanScore(data.analytics?.dimensions)
  const reach = Object.values(kpis).reduce((s, k) => s + (k.followers ?? 0), 0)

  return (
    <>
      <Board
        eyebrow={
          <>
            <Link to="/sponsor" className="hover:text-ink-2">Campaigns</Link> / athlete analytics
          </>
        }
        title={a.display_name}
        tags={
          <>
            <span className="tag">{a.sport}</span>
            <span className="tag">{a.country}</span>
            <CoverageChip coverage={data.analytics?.coverage.platforms ?? null} />
          </>
        }
        score={overall === null ? null : Math.round(overall)}
        scoreLabel="Marketability"
        deltaNote={
          computedDims
            ? `mean of ${computedDims} computed dimension${computedDims === 1 ? '' : 's'}`
            : 'not computed'
        }
        trendEmpty={
          campaignId
            ? `Audience fit below is scored against campaign #${campaignId}'s target, not a generic one.`
            : 'Open this from a campaign to score audience fit against that brief.'
        }
        figures={[
          { label: 'Rate card', value: fmtMoney(a.base_rate_eur) },
          { label: 'Total reach', value: fmtNum(reach) },
          { label: 'Posts analysed', value: data.posts.length },
          { label: 'Platforms', value: `${data.analytics?.coverage.platforms.connected ?? 0} of ${data.analytics?.coverage.platforms.total ?? 3}` },
        ]}
        footNote={a.bio ? undefined : 'no bio published'}
      />

      <div>
      {a.bio && <p className="mt-6 max-w-2xl text-sm text-ink-2">{a.bio}</p>}

      <Section title="Marketability dimensions">
        {data.analytics ? (
          <DimensionGrid score={{ dimensions: data.analytics.dimensions }} />
        ) : (
          <EmptyNote text={`Analytics unavailable: ${(data.analytics_unavailable ?? 'no connected platforms').replace(/_/g, ' ')}. Commercial signals only.`} />
        )}
      </Section>

      {Object.keys(kpis).length > 0 && (
        <Section title="Per-platform inputs (evidence)">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="table-head">Platform</th>
                  <th className="table-head text-right">Followers</th>
                  <th className="table-head text-right">Median reach</th>
                  <th className="table-head text-right">Median ER</th>
                  <th className="table-head text-right">Posts / wk</th>
                  <th className="table-head text-right">Growth 30d</th>
                  <th className="table-head text-right">Posts in window</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(kpis).map(([platform, k]) => (
                  <tr key={platform}>
                    <td className="table-cell text-ink">{platformLabel(platform)}</td>
                    <td className="table-cell tnum text-right">{fmtNum(k.followers)}</td>
                    <td className="table-cell tnum text-right">{fmtNum(k.median_reach)}</td>
                    <td className="table-cell tnum text-right">{fmtPct(k.median_er, 2)}</td>
                    <td className="table-cell tnum text-right">{k.cadence_per_week ?? '—'}</td>
                    <td className="table-cell tnum text-right">{fmtPct(k.growth_30d)}</td>
                    <td className="table-cell tnum text-right">{k.posts_in_window}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {Object.keys(data.audience).length > 0 && (
        <Section title="Audience">
          <AudiencePanel audience={data.audience} />
        </Section>
      )}

      {data.posts.length > 0 && (
        <Section title="Recent content (latest metric capture per post)">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Published</th>
                <th className="table-head">Platform</th>
                <th className="table-head">Title</th>
                <th className="table-head text-right">Reach</th>
                <th className="table-head text-right">ER</th>
              </tr>
            </thead>
            <tbody>
              {data.posts.map((p, i) => (
                <tr key={i}>
                  <td className="table-cell text-xs text-ink-3">{fmtDate(p.published_at)}</td>
                  <td className="table-cell">{platformLabel(p.platform)}</td>
                  <td className="table-cell max-w-64 truncate text-ink">{p.title}</td>
                  <td className="table-cell tnum text-right">{fmtNum(p.reach)}</td>
                  <td className="table-cell tnum text-right">{fmtPct(p.engagement_rate, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
      </div>
    </>
  )
}
