import { Shield } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AudiencePanel } from '../components/charts'
import { LoadError, PageLoading, Avatar, CoverageChip, DimensionGrid, Section } from '../components/ui'
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

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Shield size={13} className="text-mist-400" />
        {(a.clubs ?? []).length > 0 ? (
          (a.clubs ?? []).map((c) => (
            <Link key={c.slug} to={`/clubs/${c.slug}`}
                  className="chip border-pulse-500 text-mist-100 hover:shadow-card"
                  title={c.position ? `${c.position} — view club` : 'View club'}>
              {c.name}{c.position ? ` · ${c.position}` : ''}
            </Link>
          ))
        ) : (
          <span className="text-xs text-mist-400">Independent — no club affiliation</span>
        )}
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
          <AudiencePanel audience={a.audience} />
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
