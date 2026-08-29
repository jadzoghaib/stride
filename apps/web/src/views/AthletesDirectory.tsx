import { ArrowDown, ArrowUp } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, CoverageChip, EmptyNote, LoadError, Meter, PageHeader, PageLoading } from '../components/ui'
import { api, errorText } from '../lib/api'
import { fmtMoney } from '../lib/format'
import type { AthletePage, AthletePublic } from '../types'
import { meanScore } from '../types'

type SortKey = 'display_name' | 'score' | 'base_rate_eur'

const COLUMNS: { key: SortKey; label: string; align?: string }[] = [
  { key: 'display_name', label: 'Athlete' },
  { key: 'score', label: 'Marketability', align: 'text-right' },
  { key: 'base_rate_eur', label: 'Rate card', align: 'text-right' },
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
  const [cursor, setCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  useEffect(() => {
    api.get<{ sports: string[]; countries: string[] }>('/api/athletes/facets').then(setFacets).catch(() => {})
  }, [])

  /** Typing is not a query. Every keystroke used to be a request that ran a
   *  LIKE across the directory and a score lookup per row; the search box now
   *  settles first. 250ms is below the threshold where a filter feels laggy and
   *  well above a typing cadence.
   *
   *  The input binds to `typed` and only this timer writes `q`. Binding it to
   *  `q` directly — which it did — left this timer running over a value nothing
   *  produced, so every keystroke still fetched and the debounce was decoration.
   */
  const [typed, setTyped] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setQ(typed), 250)
    return () => clearTimeout(t)
  }, [typed])

  const params = (cursor?: string) => {
    const p = new URLSearchParams()
    if (sport) p.set('sport', sport)
    if (country) p.set('country', country)
    if (q) p.set('q', q)
    if (cursor) p.set('cursor', cursor)
    return p
  }

  const [searching, setSearching] = useState(false)
  //: Which query the visible rows belong to. Keeping the old results on screen
  //  is what makes the box usable, and it is also what makes a late response
  //  dangerous: two searches in flight can resolve out of order, and the loser
  //  would quietly repaint the table with rows for a query the user has already
  //  moved past. Only the newest request is allowed to write anything.
  const latest = useRef(0)
  useEffect(() => {
    setError('')
    // Not `setAthletes(null)`. That tripped the `!athletes` guard below, which
    // returns a full-page skeleton — unmounting the search box mid-word, so the
    // field lost focus and dropped the keystroke that triggered it. The previous
    // results stay on screen while the next ones load, which is also the calmer
    // thing to look at.
    const mine = ++latest.current
    setSearching(true)
    api.get<AthletePage>(`/api/athletes?${params()}`)
      .then((page) => {
        if (mine !== latest.current) return
        setAthletes(page.athletes)
        setCursor(page.next_cursor)
      })
      .catch((e) => { if (mine === latest.current) setError(errorText(e)) })
      .finally(() => { if (mine === latest.current) setSearching(false) })
  }, [sport, country, q])

  const loadMore = async () => {
    if (!cursor || searching) return
    // Same generation check as the search effect. Changing a filter while page
    // two is in flight would otherwise append the *previous* query's rows to
    // the new results and overwrite the cursor with a pointer into the old
    // query — rows that do not match, presented as though they do.
    const mine = latest.current
    setLoadingMore(true)
    try {
      const page = await api.get<AthletePage>(`/api/athletes?${params(cursor)}`)
      if (mine !== latest.current) return
      setAthletes((a) => [...(a ?? []), ...page.athletes])
      setCursor(page.next_cursor)
    } catch (e) {
      if (mine === latest.current) setError(errorText(e))
    } finally {
      if (mine === latest.current) setLoadingMore(false)
    }
  }

  /** The directory is the browse surface for a product that measures
   *  marketability, so it shows the measurement. The API already returns the
   *  full dimension set here; the composite is the same client-side mean the
   *  dashboards use, and is labelled as derived in the column note. */
  const rows = useMemo(() => {
    const scored = (athletes ?? []).map((a) => ({ ...a, mean: meanScore(a.score?.dimensions).value }))
    const dir = desc ? -1 : 1
    return scored.sort((a, b) => {
      if (sort === 'display_name') return dir * a.display_name.localeCompare(b.display_name)
      if (sort === 'base_rate_eur') return dir * (a.base_rate_eur - b.base_rate_eur)
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

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <input
            className="field w-56 py-1.5 pr-[5.5rem] text-sm"
            placeholder="Search name or sport"
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            aria-busy={searching}
          />
          {/* Keeping the previous results on screen means nothing else moves
              while a search runs, so this is the only sign it is running. */}
          {searching && (
            <span className="meta absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3">
              searching…
            </span>
          )}
        </div>
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
                <td className="table-cell tnum text-right">{fmtMoney(a.base_rate_eur)}</td>
                <td className="table-cell">{a.sport}</td>
                <td className="table-cell">{a.country}</td>
                <td className="table-cell">
                  <CoverageChip coverage={a.score?.coverage ?? null} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {cursor && (
          <div className="mt-4 flex justify-center">
            {/* Disabled mid-search: `cursor` still points into the *previous*
                query's results, so paging now would append rows the current
                filters exclude — and they would look like matches. */}
            <button className="btn" disabled={loadingMore || searching} onClick={loadMore}>
              {loadingMore ? 'Loading…' : 'Show more athletes'}
            </button>
          </div>
        )}
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
