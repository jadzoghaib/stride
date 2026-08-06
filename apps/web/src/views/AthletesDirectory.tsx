import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, CoverageChip, EmptyNote } from '../components/ui'
import { api, errorText } from '../lib/api'
import { fmtMoney } from '../lib/format'
import type { AthletePublic } from '../types'

export default function AthletesDirectory() {
  const [athletes, setAthletes] = useState<AthletePublic[] | null>(null)
  const [facets, setFacets] = useState<{ sports: string[]; countries: string[] }>({ sports: [], countries: [] })
  const [sport, setSport] = useState('')
  const [country, setCountry] = useState('')
  const [q, setQ] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ sports: string[]; countries: string[] }>('/api/athletes/facets').then(setFacets).catch(() => {})
  }, [])

  useEffect(() => {
    const p = new URLSearchParams()
    if (sport) p.set('sport', sport)
    if (country) p.set('country', country)
    if (q) p.set('q', q)
    api.get<AthletePublic[]>(`/api/athletes?${p}`).then(setAthletes).catch((e) => setError(errorText(e)))
  }, [sport, country, q])

  return (
    <div>
      <h1 className="text-2xl font-semibold text-ink">Athlete directory</h1>
      <div className="mt-4 flex flex-wrap gap-2">
        <input className="field w-56 py-1.5 text-sm" placeholder="Search name or sport" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="field w-44 py-1.5 text-sm" value={sport} onChange={(e) => setSport(e.target.value)}>
          <option value="">All sports</option>
          {facets.sports.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select className="field w-44 py-1.5 text-sm" value={country} onChange={(e) => setCountry(e.target.value)}>
          <option value="">All countries</option>
          {facets.countries.map((c) => <option key={c}>{c}</option>)}
        </select>
      </div>
      {error && <div className="mt-4 text-sm text-critical">{error}</div>}
      <div className="mt-6 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="table-head">Athlete</th>
              <th className="table-head">Sport</th>
              <th className="table-head">Country</th>
              <th className="table-head text-right">Rate card</th>
              <th className="table-head">Analytics coverage</th>
            </tr>
          </thead>
          <tbody>
            {athletes?.map((a) => (
              <tr key={a.id}>
                <td className="table-cell">
                  <Link to={`/athletes/${a.slug}`} className="flex items-center gap-2.5 text-ink hover:text-accent">
                    <Avatar name={a.display_name} size={28} /> {a.display_name}
                  </Link>
                </td>
                <td className="table-cell">{a.sport}</td>
                <td className="table-cell">{a.country}</td>
                <td className="table-cell tnum text-right">{fmtMoney(a.base_rate_usd)}</td>
                <td className="table-cell"><CoverageChip coverage={a.score?.coverage ?? null} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {athletes && athletes.length === 0 && <div className="mt-4"><EmptyNote text="No athletes match those filters." /></div>}
    </div>
  )
}
