import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { LoadError, PageLoading, Avatar, CoverageChip, DimensionGrid, Section, ShareBar } from '../components/ui'
import { api, errorText } from '../lib/api'
import { fmtMoney } from '../lib/format'
import type { AthletePublic as Athlete } from '../types'
import { dealTypeLabel } from '../types'

export default function AthletePublicView() {
  const { slug } = useParams()
  const [a, setA] = useState<Athlete | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Athlete>(`/api/athletes/${slug}`).then(setA).catch((e) => setError(errorText(e)))
  }, [slug])

  if (!a) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      <div className="flex flex-wrap items-center gap-4">
        <Avatar name={a.display_name} size={56} />
        <div>
          <h1 className="text-2xl font-semibold text-mist-100">{a.display_name}</h1>
          <div className="text-sm text-mist-400">{a.sport} · {a.country} · {a.region}</div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="chip tnum">rate {fmtMoney(a.base_rate_usd)}</span>
          <CoverageChip coverage={a.score?.coverage ?? null} />
        </div>
      </div>

      {a.bio && <p className="mt-4 max-w-2xl text-sm text-mist-300">{a.bio}</p>}

      {a.career_highlights.length > 0 && (
        <Section title="Career highlights">
          <ul className="space-y-1 text-sm text-mist-300">
            {a.career_highlights.map((h) => <li key={h} className="flex gap-2"><span className="text-pulse-400">—</span>{h}</li>)}
          </ul>
        </Section>
      )}

      <Section title="Marketability">
        <DimensionGrid score={a.score} />
      </Section>

      {a.audience && Object.keys(a.audience).length > 0 && (
        <Section title="Audience">
          <div className="grid gap-6 md:grid-cols-3">
            {(['age', 'gender', 'country'] as const).map((dim) =>
              a.audience![dim] ? (
                <div key={dim}>
                  <div className="microcaps mb-2">{dim}</div>
                  <ShareBar data={a.audience![dim]} />
                </div>
              ) : null,
            )}
          </div>
        </Section>
      )}

      <Section title="Open to">
        <div className="flex flex-wrap gap-2">
          {a.deal_types.map((t) => <span key={t} className="chip">{dealTypeLabel(t)}</span>)}
          {a.topics.map((t) => <span key={t} className="chip text-mist-400">{t}</span>)}
        </div>
      </Section>
    </div>
  )
}
