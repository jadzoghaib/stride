import { RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AudiencePanel } from '../../components/charts'
import { LoadError, PageLoading, CoverageChip, DimensionGrid, EmptyNote, Section, Stat, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDT, fmtMoney, fmtNum } from '../../lib/format'
import type { AthleteWorkspace } from '../../types'
import { DIMENSIONS } from '../../types'

const PLATFORMS = ['instagram', 'youtube', 'tiktok']

export default function AthleteDashboard() {
  const [ws, setWs] = useState<AthleteWorkspace | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [evidence, setEvidence] = useState<string | null>(null)

  const load = () => api.get<AthleteWorkspace>('/api/athlete/workspace').then(setWs).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [])

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true)
    setError('')
    try {
      await fn()
      await load()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  if (!ws) return error ? <LoadError text={error} /> : <PageLoading />

  const connected = new Set(ws.accounts.filter((a) => a.connection_status === 'connected').map((a) => a.platform))
  const available = PLATFORMS.filter((p) => !connected.has(p))
  const openDeals = ws.deals.filter((d) => d.status === 'offered')

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-mist-100">{ws.profile.display_name}</h1>
        <span className="chip">{ws.profile.sport}</span>
        <span className="chip">{ws.profile.country}</span>
        <StatusChip status={ws.editable.status} />
        <CoverageChip coverage={ws.profile.score?.coverage ?? null} />
        {(ws.clubs ?? []).map((c) => (
          <Link key={c.slug} to={`/clubs/${c.slug}`} className="chip border-pulse-500 text-mist-100 hover:shadow-card"
                title={c.position ? `${c.position} — view club` : 'View club'}>
            {c.name}
          </Link>
        ))}
      </div>

      {error && <div className="mt-4 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}

      {(ws.club_backing ?? []).length > 0 && (
        <div className="mt-4 rounded-lg border border-ok/40 bg-ok/10 px-4 py-3 text-sm">
          <div className="microcaps mb-1">Club-routed backing</div>
          {ws.club_backing.map((b, i) => (
            <div key={i} className="text-mist-200">
              {b.org_name} backs you through {b.club_name} — {b.package_name} ({fmtMoney(b.amount_usd)})
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <Stat label="Committed earnings" value={fmtMoney(ws.earnings)} sub="accepted + completed deals"
              to="/athlete/deals#history" />
        <Stat label="Open offers" value={openDeals.length}
              sub={openDeals.length ? 'awaiting your response — review them' : 'nothing waiting on you'}
              to="/athlete/deals" />
        <Stat
          label="Total followers"
          value={fmtNum(ws.accounts.reduce((s, a) => s + (a.connection_status === 'connected' ? a.followers ?? 0 : 0), 0))}
          sub={`${connected.size} connected platform${connected.size === 1 ? '' : 's'}`}
          to="/athlete#platforms"
        />
      </div>

      <Section
        title="Marketability"
        aside={ws.analytics && <span className="text-xs text-mist-400">computed {fmtDT(ws.analytics.computed_at)} · formulas v{ws.analytics.formula_version}</span>}
      >
        <DimensionGrid
          score={ws.analytics ? { dimensions: ws.analytics.dimensions } : null}
          onSelect={(k) => setEvidence(evidence === k ? null : k)}
          selected={evidence}
        />
        {evidence && ws.analytics && (
          <div className="panel mt-3 border-pulse-500 p-4">
            <div className="microcaps">{DIMENSIONS.find((d) => d.key === evidence)?.label} — per-platform inputs</div>
            <EvidenceTable inputs={ws.analytics.inputs} dimension={evidence} />
            <div className="mt-2 text-xs text-mist-400">
              {(() => {
                const cov = ws.analytics!.coverage.dimensions[evidence]
                return cov?.confidence
                  ? `Confidence ${cov.confidence} (${cov.data_points} ${String(cov.unit ?? '').replace(/_/g, ' ')})`
                  : `Unavailable: ${String(cov?.reason ?? 'no data').replace(/_/g, ' ')}`
              })()}
            </div>
          </div>
        )}
      </Section>

      <Section title="Connected platforms" id="platforms">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Platform</th>
                <th className="table-head">Status</th>
                <th className="table-head text-right">Followers</th>
                <th className="table-head">Last sync</th>
                <th className="table-head" />
              </tr>
            </thead>
            <tbody>
              {ws.accounts.map((a) => (
                <tr key={a.id}>
                  <td className="table-cell capitalize text-mist-100">{a.platform}</td>
                  <td className="table-cell"><StatusChip status={a.connection_status} /></td>
                  <td className="table-cell tnum text-right">{fmtNum(a.followers)}</td>
                  <td className="table-cell text-xs text-mist-400">
                    {a.last_run ? `${a.last_run.status} · ${fmtDT(a.last_run.finished_at)}` : 'never'}
                    {a.last_run?.error && <span className="text-danger"> — {a.last_run.error}</span>}
                  </td>
                  <td className="table-cell text-right">
                    {a.connection_status === 'connected' && (
                      <button className="btn px-2.5 py-1 text-xs" disabled={busy}
                              onClick={() => act(() => api.post(`/api/athlete/platforms/${a.id}/sync`))}>
                        <RefreshCw size={12} /> Sync
                      </button>
                    )}
                  </td>
                </tr>
              ))}
              {ws.accounts.length === 0 && (
                <tr><td className="table-cell text-mist-400" colSpan={5}>No platforms connected yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {available.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className="microcaps">Connect</span>
            {available.map((p) => (
              <button key={p} className="btn capitalize" disabled={busy}
                      onClick={() => act(() => api.post('/api/athlete/platforms/connect', { platform: p }))}>
                {p}
              </button>
            ))}
            <span className="text-xs text-mist-400">First iteration uses simulated platform data behind the production connector interface.</span>
          </div>
        )}
      </Section>

      <Section title="Audience" id="audience">
        {Object.keys(ws.audience).length ? (
          <AudiencePanel audience={ws.audience} />
        ) : (
          <EmptyNote text="Audience demographics appear after your first platform sync." />
        )}
      </Section>
    </div>
  )
}

function EvidenceTable({ inputs, dimension }: { inputs: NonNullable<AthleteWorkspace['analytics']>['inputs']; dimension: string }) {
  const inter = (inputs.intermediate as Record<string, Record<string, unknown>>)[dimension]
  if (!inter) return <div className="mt-2 text-sm text-mist-400">No inputs recorded for this dimension.</div>
  const platformKeyed = Object.values(inter).every((v) => typeof v === 'object' && v !== null)
  const rows = platformKeyed && !('total_followers' in inter)
    ? Object.entries(inter as Record<string, Record<string, number>>)
    : [['inputs', inter as Record<string, number>] as const]
  const cols = Object.keys(rows[0][1])
  return (
    <div className="mt-2 overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="table-head">Source</th>
            {cols.map((c) => <th key={c} className="table-head text-right">{c.replace(/_/g, ' ')}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, vals]) => (
            <tr key={String(name)}>
              <td className="table-cell capitalize text-mist-100">{String(name)}</td>
              {cols.map((c) => (
                <td key={c} className="table-cell tnum text-right">{String((vals as Record<string, unknown>)[c] ?? '—')}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
