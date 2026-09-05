/** Admin surface: the audit log, and the chaos controls the failure drill uses.
 *
 *  /api/admin has existed since the first draft; the client never had a route
 *  for it, so the admin nav entry resolved to a 404 while rendering as the
 *  active tab. This is the thin version — a table and the drill controls. */

import { useEffect, useState } from 'react'
import { EmptyNote, LoadError, PageHeader, PageLoading, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useToast } from '../../lib/toast'
import { fmtDT } from '../../lib/format'

/** Mirrors the `events` table columns exactly — they are `object_*`, not
 *  `entity_*`. A mismatch here is invisible to the typechecker (the response is
 *  an unchecked assertion at the fetch boundary) and shows up only as a column
 *  full of em-dashes, which is how the first version of this view shipped. */
interface AuditEvent {
  id: number
  ts: string
  actor: string
  event_type: string
  object_type: string | null
  object_id: number | null
  detail: Record<string, unknown>
}

interface ChaosState {
  enabled: boolean
  latency_ms: number
  error_rate: number
  db_down: boolean
}

export default function Operations() {
  const [events, setEvents] = useState<AuditEvent[] | null>(null)
  const [chaos, setChaos] = useState<ChaosState | null>(null)
  const [filter, setFilter] = useState('')
  const [error, setError] = useState('')
  const toast = useToast()

  const load = async () => {
    const [e, c] = await Promise.all([
      api.get<AuditEvent[]>('/api/admin/events?limit=200'),
      api.get<ChaosState>('/api/admin/chaos'),
    ])
    setEvents(e)
    setChaos(c)
  }

  useEffect(() => {
    load().catch((e) => setError(errorText(e)))
  }, [])

  const inject = async (body: Partial<ChaosState>) => {
    setError('')
    try {
      setChaos(await api.post<ChaosState>('/api/admin/chaos', {
        latency_ms: 0, error_rate: 0, db_down: false, ...body,
      }))
      toast('Chaos state applied')
    } catch (e) {
      setError(errorText(e))
    }
  }

  const reset = async () => {
    setError('')
    try {
      setChaos(await api.post<ChaosState>('/api/admin/chaos/reset'))
      toast('Chaos reset — system nominal')
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!events || !chaos) return error ? <LoadError text={error} /> : <PageLoading />

  const active = chaos.latency_ms > 0 || chaos.error_rate > 0 || chaos.db_down
  const types = [...new Set(events.map((e) => e.event_type))].sort()
  const shown = filter ? events.filter((e) => e.event_type === filter) : events

  return (
    <div>
      <PageHeader
        eyebrow="Admin"
        title="Operations"
        lede="Every account action lands in the audit log. The chaos controls drive the same failure injection scripts/failure_drill.py uses."
        // "error" was wrong: the faults on this page are injected by whoever is
        // reading it, and labelling a drill as an error means a glance at this
        // header cannot tell a rehearsal from a real outage — which is the one
        // job a status chip has.
        aside={<StatusChip status={active ? 'drill running' : 'connected'} />}
      />

      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      <Section
        title="Resilience drill"
        aside={<span className="meta">{chaos.enabled ? 'injection enabled' : 'disabled in this environment'}</span>}
      >
        <div className="panel p-5">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div className="flex items-baseline gap-2.5">
              <span className="cap">Latency</span>
              <b className="tnum font-display text-lead font-bold text-ink">{chaos.latency_ms}ms</b>
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="cap">Error rate</span>
              <b className="tnum font-display text-lead font-bold text-ink">
                {(100 * chaos.error_rate).toFixed(0)}%
              </b>
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="cap">Database</span>
              <b className="font-display text-lead font-bold text-ink">
                {chaos.db_down ? 'unreachable' : 'reachable'}
              </b>
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <button className="btn" disabled={!chaos.enabled} onClick={() => inject({ latency_ms: 400 })}>
              Inject 400ms latency
            </button>
            <button className="btn" disabled={!chaos.enabled} onClick={() => inject({ error_rate: 0.5 })}>
              Fail 50% of requests
            </button>
            <button className="btn" disabled={!chaos.enabled} onClick={() => inject({ db_down: true })}>
              Take the database down
            </button>
            <button className="btn-go" disabled={!active} onClick={reset}>
              Reset
            </button>
          </div>
          <p className="meta mt-3">
            Taking the database down fails <code>/readyz</code> while <code>/healthz</code> keeps passing —
            Kubernetes stops routing to the pod instead of restarting it.
          </p>
        </div>
      </Section>

      <Section
        title="Audit log"
        aside={
          <select
            className="field w-56 py-1 text-xs"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            aria-label="Filter by event type"
          >
            <option value="">All event types ({events.length})</option>
            {types.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        }
      >
        {shown.length === 0 ? (
          <EmptyNote text="No events of that type recorded yet." />
        ) : (
          <div className="panel overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className="table-head">When</th>
                  <th className="table-head">Actor</th>
                  <th className="table-head">Event</th>
                  <th className="table-head">Entity</th>
                  <th className="table-head">Detail</th>
                </tr>
              </thead>
              <tbody>
                {shown.slice(0, 100).map((e) => (
                  <tr key={e.id}>
                    <td className="table-cell meta whitespace-nowrap">{fmtDT(e.ts)}</td>
                    <td className="table-cell">
                      <span className="tag">{e.actor}</span>
                    </td>
                    <td className="table-cell font-display font-semibold uppercase tracking-board text-ink">
                      {e.event_type}
                    </td>
                    <td className="table-cell meta">
                      {e.object_type ? `${e.object_type}#${e.object_id}` : '—'}
                    </td>
                    <td className="table-cell meta max-w-md truncate" title={JSON.stringify(e.detail)}>
                      {JSON.stringify(e.detail)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {shown.length > 100 && (
          <p className="meta mt-3">Showing the 100 most recent of {shown.length} matching events.</p>
        )}
      </Section>
    </div>
  )
}
