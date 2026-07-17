import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { Avatar, CoverageChip, DimensionGrid, EmptyNote, Section, ShareBar } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney, fmtNum, fmtPct } from '../../lib/format'
import type { AthletePublic } from '../../types'

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

  if (!data) return <div className="text-mist-400">{error || 'Assembling evidence…'}</div>

  const a = data.athlete
  const kpis = data.analytics?.inputs.platform_kpis ?? {}

  return (
    <div>
      <div className="text-xs text-mist-400">
        <Link to="/sponsor" className="hover:text-mist-200">Campaigns</Link> / athlete analytics
        {campaignId && <span> · scored against campaign #{campaignId}'s target</span>}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-4">
        <Avatar name={a.display_name} size={52} />
        <div>
          <h1 className="text-2xl font-semibold text-mist-100">{a.display_name}</h1>
          <div className="text-sm text-mist-400">{a.sport} · {a.country} · rate {fmtMoney(a.base_rate_usd)}</div>
        </div>
        <div className="ml-auto"><CoverageChip coverage={a.score?.coverage ?? null} /></div>
      </div>
      {a.bio && <p className="mt-3 max-w-2xl text-sm text-mist-300">{a.bio}</p>}

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
                    <td className="table-cell capitalize text-mist-100">{platform}</td>
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
          <div className="grid gap-6 md:grid-cols-3">
            {(['age', 'gender', 'country'] as const).map((dim) =>
              data.audience[dim] ? (
                <div key={dim}>
                  <div className="microcaps mb-2">{dim}</div>
                  <ShareBar data={data.audience[dim]} />
                </div>
              ) : null,
            )}
          </div>
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
                  <td className="table-cell text-xs text-mist-400">{fmtDate(p.published_at)}</td>
                  <td className="table-cell capitalize">{p.platform}</td>
                  <td className="table-cell max-w-64 truncate text-mist-100">{p.title}</td>
                  <td className="table-cell tnum text-right">{fmtNum(p.reach)}</td>
                  <td className="table-cell tnum text-right">{fmtPct(p.engagement_rate, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
    </div>
  )
}
