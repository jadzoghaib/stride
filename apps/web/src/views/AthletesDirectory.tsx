import { ArrowDown, ArrowUp } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, CoverageChip, EmptyNote, LoadError, Meter, PageHeader, PageLoading } from '../components/ui'
import { api, errorText } from '../lib/api'
import { fmtMoney } from '../lib/format'
import type { AthletePublic } from '../types'
import { meanScore } from '../types'

type SortKey = 'display_name' | 'score' | 'base_rate_usd'

const COLUMNS: { key: SortKey; label: string; align?: string }[] = [
  { key: 'display_name', label: 'Athlete' },
  { key: 'score', label: 'Marketability', align: 'text-right' },
  { key: 'base_rate_usd', label: 'Rate card', align: 'text-right' },
]

export default function AthletesDirectory() {
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [facets, setFacets] = useState<{ sports: string[]; countries: string[] }>({ sports: [], countries: [] })
  const [sport, setSport] = useState('')
  const [country, setCountry] = useState('')
  const [q, setQ] = useState('')
  const [sort, setSort] = useState<SortKey>('score')
  const [desc, setDesc] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ sports: string[]; countries: string[] }>('/api/athletes/facets').then(setFacets).catch(() => {})
  }, [])

  useEffect(() => {
    const p = new URLSearchParams()
    if (sport) p.set('sport', sport)
    if (country) p.set('country', country)
    if (q) p.set('q', q)
    setError('')
    api.get<AthletePublic[]>(`/api/athletes?${p}`).then(setAthletes).catch((e) => setError(errorText(e)))
  }, [sport, country, q])

  /** The directory is the browse surface for a product that measures
   *  marketability, so it shows the measurement. The API already returns the
   *  full dimension set here; the composite is the same client-side mean the
   *  dashboards use, and is labelled as derived in the column note. */
  const rows = useMemo(() => {
    const scored = (athletes ?? []).map((a) => ({ ...a, mean: meanScore(a.score?.dimensions).value }))
    const dir = desc ? -1 : 1
    return scored.sort((a, b) => {
      if (sort === 'display_name') return dir * a.display_name.localeCompare(b.display_name)
      if (sort === 'base_rate_usd') return dir * (a.base_rate_usd - b.base_rate_usd)
      // unscored athletes sort last in both directions — an absent score is not
      // a low score, so it never displaces a measured one at the top
      if (a.mean === null || b.mean === null) return a.mean === b.mean ? 0 : a.mean === null ? 1 : -1
      return dir * (a.mean - b.mean)
    })
  }, [athletes, sort, desc])

  if (!athletes) return error ? <LoadError text={error} /> : <PageLoading />

  const toggle = (key: SortKey) => {
    if (sort === key) setDesc((d) => !d)
    else {
      setSort(key)
      setDesc(key !== 'display_name')
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Directory"
        title="Athlete directory"
        lede="Every listed athlete, with the marketability mean behind their profile. Coverage says how many platforms that mean is computed from."
        aside={
          <span className="meta">
            {rows.length} athlete{rows.length === 1 ? '' : 's'}
          </span>
        }
      />

      <div className="flex flex-wrap gap-2">
        <input
          className="field w-56 py-1.5 text-sm"
          placeholder="Search name or sport"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className="field w-44 py-1.5 text-sm" value={sport} onChange={(e) => setSport(e.target.value)}>
          <option value="">All sports</option>
          {facets.sports.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select className="field w-44 py-1.5 text-sm" value={country} onChange={(e) => setCountry(e.target.value)}>
          <option value="">All countries</option>
          {facets.countries.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="mt-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      <div className="mt-6 panel overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              {COLUMNS.map((col) => (
                <th key={col.key} className={`table-head ${col.align ?? ''}`} aria-sort={sort === col.key ? (desc ? 'descending' : 'ascending') : 'none'}>
                  <button
                    className="inline-flex items-center gap-1 uppercase tracking-micro transition-colors hover:text-ink"
                    onClick={() => toggle(col.key)}
                  >
                    {col.label}
                    {sort === col.key &&
                      (desc ? <ArrowDown size={11} className="text-accent" /> : <ArrowUp size={11} className="text-accent" />)}
                  </button>
                </th>
              ))}
              <th className="table-head">Sport</th>
              <th className="table-head">Country</th>
              <th className="table-head">Analytics coverage</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => (
              <tr key={a.id}>
                <td className="table-cell">
                  <Link to={`/athletes/${a.slug}`} className="flex items-center gap-2.5 text-ink hover:text-accent">
                    <Avatar name={a.display_name} size={28} /> {a.display_name}
                  </Link>
                </td>
                <td className="table-cell">
                  {a.mean === null ? (
                    <span className="cap block text-right text-ink-3">not scored</span>
                  ) : (
                    <div className="ml-auto w-24">
                      <div className="tnum text-right font-display text-[19px] font-bold leading-none text-ink">
                        {Math.round(a.mean)}
                      </div>
                      <div className="mt-1.5">
                        <Meter value={a.mean} height={4} muted={a.mean < 65} />
                      </div>
                    </div>
                  )}
                </td>
                <td className="table-cell tnum text-right">{fmtMoney(a.base_rate_usd)}</td>
                <td className="table-cell">{a.sport}</td>
                <td className="table-cell">{a.country}</td>
                <td className="table-cell">
                  <CoverageChip coverage={a.score?.coverage ?? null} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="meta mt-3">
        Marketability is the mean of the dimensions computed for that athlete — a derived figure, not a
        stored one. Open a profile for the per-dimension breakdown.
      </p>
      {rows.length === 0 && (
        <div className="mt-4">
          <EmptyNote text="No athletes match those filters." />
        </div>
      )}
    </div>
  )
}
