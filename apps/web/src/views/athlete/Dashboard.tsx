import { RefreshCw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Board } from '../../components/Board'
import { AudiencePanel } from '../../components/charts'
import {
  CoverageChip,
  DimensionGrid,
  EmptyNote,
  LoadError,
  Modal,
  PageLoading,
  Section,
  StatusChip,
} from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useToast } from '../../lib/toast'
import { fmtDT, fmtMoney, fmtNum } from '../../lib/format'
import { POLICY_VERSION } from '../../lib/legal'
import type { AthleteWorkspace, ClubInvitation } from '../../types'
import { DIMENSIONS, meanScore, platformLabel } from '../../types'

const PLATFORMS = ['instagram', 'youtube', 'tiktok']

export default function AthleteDashboard() {
  const [ws, setWs] = useState<AthleteWorkspace | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [evidence, setEvidence] = useState<string | null>(null)
  const [connecting, setConnecting] = useState<string | null>(null)
  // The withdrawal is consequential enough to confirm: it takes the platform's
  // posts off the public wall and out of the deliverables an athlete can
  // attach. Holding the account here rather than a boolean means the dialog
  // can name what is being withdrawn.
  const [dropping, setDropping] = useState<AthleteWorkspace['accounts'][number] | null>(null)

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
  const followers = ws.accounts.reduce((s, a) => s + (a.connection_status === 'connected' ? a.followers ?? 0 : 0), 0)

  const { value: overall, n: computedDims } = meanScore(ws.analytics?.dimensions)

  // The only stored history is audience scale, so that — not the headline mean —
  // is what the trend line shows, and it says so.
  const history = (ws.profile.score_history ?? [])
    .map((h) => h.audience_scale)
    .filter((v): v is number => typeof v === 'number')

  return (
    <>
      <Board
        eyebrow="Athlete"
        title={ws.profile.display_name}
        tags={
          <>
            <span className="tag">{ws.profile.sport}</span>
            <span className="tag">{ws.profile.country}</span>
            <StatusChip status={ws.editable.status} />
            <CoverageChip coverage={ws.profile.score?.coverage ?? null} />
            {(ws.clubs ?? []).map((c) => (
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
        deltaNote={computedDims ? `mean of ${computedDims} computed dimension${computedDims === 1 ? '' : 's'}` : 'not yet computed'}
        trend={history}
        trendLabel={history.length > 1 ? `audience scale · last ${history.length} snapshots` : undefined}
        trendEmpty="A trend line appears once a second sync has been recorded."
        figures={[
          { label: 'Committed', value: fmtMoney(ws.earnings), to: '/athlete/deals#history' },
          { label: 'Open offers', value: openDeals.length, to: '/athlete/deals' },
          { label: 'Total reach', value: fmtNum(followers), to: '/athlete#platforms' },
          { label: 'Base rate', value: fmtMoney(ws.editable.base_rate_eur) },
        ]}
        footNote={
          ws.analytics ? `computed ${fmtDT(ws.analytics.computed_at)} · formulas v${ws.analytics.formula_version}` : undefined
        }
      />

      <div>
        {error && (
          <div className="mt-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">{error}</div>
        )}

        {(ws.club_backing ?? []).length > 0 && (
          <div className="mt-4 rounded border border-ok/45 bg-ok/10 px-4 py-3 text-sm">
            <div className="cap mb-1">Club-routed backing</div>
            {ws.club_backing.map((b, i) => (
              <div key={i} className="text-ink-2">
                {b.org_name} backs you through {b.club_name} — {b.package_name} ({fmtMoney(b.amount_eur)})
              </div>
            ))}
          </div>
        )}

        <Section
          title="Marketability — ranked dimensions"
          aside={<span className="meta">select a lane for per-platform inputs</span>}
        >
          <DimensionGrid
            score={ws.analytics ? { dimensions: ws.analytics.dimensions } : null}
            confidence={ws.analytics?.coverage.dimensions}
            onSelect={(k) => setEvidence(evidence === k ? null : k)}
            selected={evidence}
          />
          {evidence && ws.analytics && (
            <div className="panel mt-3 border-line-strong p-4">
              <div className="cap">{DIMENSIONS.find((d) => d.key === evidence)?.label} — per-platform inputs</div>
              <EvidenceTable inputs={ws.analytics.inputs} dimension={evidence} />
              <div className="meta mt-2.5">
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

        <div className="mt-10 grid items-start gap-6 lg:grid-cols-[1.85fr_1fr]">
          <div>
            <div className="mb-4 flex items-baseline justify-between gap-4 border-b border-line-strong pb-2.5">
              {/* tabIndex -1 so focus can land here after a connect completes:
                  the button that opened the consent dialog is gone by then
                  (that platform is no longer available), so the platform's own
                  focus restoration has nothing to return to. */}
              <h2 className="cap" id="platforms" tabIndex={-1}>
                Connected platforms
              </h2>
              <span className="meta">
                {connected.size} of {PLATFORMS.length} live
              </span>
            </div>
            <div className="panel overflow-x-auto">
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
                      <td className="table-cell font-display font-semibold uppercase tracking-board text-ink">{a.platform}</td>
                      <td className="table-cell">
                        <StatusChip status={a.connection_status} />
                      </td>
                      <td className="table-cell tnum text-right font-display text-[17px] font-bold text-ink">
                        {fmtNum(a.followers)}
                      </td>
                      <td className="table-cell meta">
                        {a.last_run ? `${a.last_run.status} · ${fmtDT(a.last_run.finished_at)}` : 'never'}
                        {a.last_run?.error && <span className="text-critical"> — {a.last_run.error}</span>}
                      </td>
                      <td className="table-cell text-right">
                        {a.connection_status === 'connected' && (
                          <div className="flex items-center justify-end gap-2">
                            <button
                              className="btn"
                              disabled={busy}
                              onClick={() => act(() => api.post(`/api/athlete/platforms/${a.id}/sync`))}
                            >
                              <RefreshCw size={12} /> Sync
                            </button>
                            <button className="btn" disabled={busy} onClick={() => setDropping(a)}>
                              Disconnect
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                  {ws.accounts.length === 0 && (
                    <tr>
                      <td className="table-cell text-ink-3" colSpan={5}>
                        No platforms connected yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            {available.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <span className="cap">Connect</span>
                {available.map((p) => (
                  <button key={p} className="btn" disabled={busy} onClick={() => setConnecting(p)}>
                    {p}
                  </button>
                ))}
              </div>
            )}
            <p className="meta mt-3">
              First iteration uses simulated platform data behind the production connector interface.
            </p>
          </div>

          <div>
            <div className="mb-4 flex items-baseline justify-between gap-4 border-b border-line-strong pb-2.5">
              <h2 className="cap">Awaiting you</h2>
              <span className="meta">{openDeals.length}</span>
            </div>
            {openDeals.length === 0 ? (
              <EmptyNote text="Nothing waiting on you." />
            ) : (
              <div className="panel">
                {openDeals.map((d) => (
                  <div key={d.id} className="relative border-b border-line px-4 py-4 last:border-b-0">
                    {/* stripe marks "needs your response" — it appears on no other state */}
                    <span className="absolute bottom-0 left-0 top-0 w-[3px] bg-accent" aria-hidden />
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="font-display text-[15px] font-semibold uppercase tracking-board text-ink">
                        {d.org_name}
                      </span>
                      <span className="tnum font-display text-[21px] font-bold text-ink">{fmtMoney(d.amount_eur)}</span>
                    </div>
                    <p className="meta mt-1">
                      {d.deal_type.replace(/_/g, ' ')} · {d.category} · offered {fmtDT(d.created_at).slice(0, 10)}
                    </p>
                    {d.message && <p className="mt-2 text-sm">{d.message}</p>}
                    <div className="mt-3 flex gap-2">
                      <button
                        className="btn-go"
                        disabled={busy}
                        onClick={() => act(() => api.post(`/api/athlete/deals/${d.id}/respond`, { action: 'accept' }))}
                      >
                        Accept
                      </button>
                      <button
                        className="btn"
                        disabled={busy}
                        onClick={() => act(() => api.post(`/api/athlete/deals/${d.id}/respond`, { action: 'decline' }))}
                      >
                        Decline
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <ClubInvitations />

        <Section title="Audience" id="audience">
          {Object.keys(ws.audience).length ? (
            <AudiencePanel audience={ws.audience} />
          ) : (
            <EmptyNote text="Audience demographics appear after your first platform sync." />
          )}
        </Section>
      </div>

      {dropping && (
        <Modal title={`Disconnect ${dropping.platform}?`} onClose={() => setDropping(null)}>
          {(close) => (
            <div className="space-y-4">
              <p className="text-sm text-ink-2">
                Its posts come off your public wall immediately and stop being available to
                attach to a deal. Your scores keep the history they were computed from, so
                past deals stay auditable — but nothing new is collected from {dropping.platform}.
              </p>
              <p className="meta">You can connect it again later. The withdrawal is recorded either way.</p>
              <div className="flex items-center gap-3">
                <button className="btn-go" disabled={busy}
                        onClick={() => { close(); setDropping(null)
                          void act(() => api.post(`/api/athlete/platforms/${dropping.id}/disconnect`)) }}>
                  Disconnect {dropping.platform}
                </button>
                <button className="btn" onClick={() => { close(); setDropping(null) }}>Keep it connected</button>
              </div>
            </div>
          )}
        </Modal>
      )}

      {connecting && (
        <ConsentDialog
          platform={connecting}
          busy={busy}
          onClose={() => setConnecting(null)}
          onGrant={async (platform) => {
            await act(() =>
              api.post('/api/athlete/platforms/connect', {
                platform,
                consent: true,
                policy_version: POLICY_VERSION,
              }),
            )
            // the trigger no longer exists — put the keyboard somewhere useful
            document.getElementById('platforms')?.focus()
          }}
        />
      )}
    </>
  )
}

/** Consent is the lawful basis for everything ingested from a platform, so it is
 *  taken here — specifically, before the connection — rather than inferred from
 *  a click on a button labelled with a platform name. The scopes listed are the
 *  scopes the server records. */
function ConsentDialog({
  platform,
  busy,
  onGrant,
  onClose,
}: {
  platform: string
  busy: boolean
  /** Runs after the dialog has closed through the platform, so focus lands back
   *  on the control that opened it. Never unmount the Modal directly instead —
   *  that skips the close and drops focus on <body>. */
  onGrant: (platform: string) => void
  onClose: () => void
}) {
  const [agreed, setAgreed] = useState(false)
  return (
    <Modal title={`Connect ${platformLabel(platform)}`} onClose={onClose}>
      {(close) => (
        <>
          <p className="text-sm text-ink-2">
            Stride will read the following from your {platformLabel(platform)} account and use it to
            compute your marketability analytics. Sponsors see the result and the evidence behind it.
          </p>
          <ul className="mt-4 space-y-2 text-sm text-ink-2">
            {[
              ['Profile metrics', 'Follower count and its history over time'],
              ['Post performance', 'Reach, engagement and posting cadence for recent posts'],
              ['Aggregated audience', 'Age bands, gender split and country shares — never who your followers are'],
            ].map(([h, d]) => (
              <li key={h} className="flex gap-2.5">
                <span className="mt-2 h-px w-3 shrink-0 bg-accent" aria-hidden />
                <span>
                  <b className="text-ink">{h}</b> — {d}
                </span>
              </li>
            ))}
          </ul>
          <p className="meta mt-4 leading-relaxed">
            You can disconnect at any time, which stops collection and removes this platform from
            future scores. Your consent and any withdrawal are recorded in the audit log. See the{' '}
            <Link to="/legal/privacy" className="text-accent-ink hover:underline">
              Privacy Policy
            </Link>
            .
          </p>
          <label className="mt-4 flex cursor-pointer items-start gap-2.5 text-sm text-ink-2">
            <input
              type="checkbox"
              className="mt-1 accent-[rgb(var(--c-accent))]"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />
            <span>
              This is my account, and I consent to Stride collecting the data listed above.
            </span>
          </label>
          <div className="mt-5 flex gap-2">
            <button
              className="btn-go"
              disabled={!agreed || busy}
              onClick={() => {
                close() // through the platform, so focus returns to the trigger
                onGrant(platform)
              }}
            >
              Connect {platformLabel(platform)}
            </button>
            <button className="btn" onClick={close}>
              Cancel
            </button>
          </div>
        </>
      )}
    </Modal>
  )
}

function EvidenceTable({ inputs, dimension }: { inputs: NonNullable<AthleteWorkspace['analytics']>['inputs']; dimension: string }) {
  const inter = (inputs.intermediate as Record<string, Record<string, unknown>>)[dimension]
  if (!inter) return <div className="mt-2 text-sm text-ink-3">No inputs recorded for this dimension.</div>
  const platformKeyed = Object.values(inter).every((v) => typeof v === 'object' && v !== null)
  const rows =
    platformKeyed && !('total_followers' in inter)
      ? Object.entries(inter as Record<string, Record<string, number>>)
      : [['inputs', inter as Record<string, number>] as const]
  const cols = Object.keys(rows[0][1])
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="table-head">Source</th>
            {cols.map((c) => (
              <th key={c} className="table-head text-right">
                {c.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([name, vals]) => (
            <tr key={String(name)}>
              <td className="table-cell font-display font-semibold uppercase tracking-board text-ink">{String(name)}</td>
              {cols.map((c) => (
                <td key={c} className="table-cell tnum text-right">
                  {String((vals as Record<string, unknown>)[c] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Clubs that have asked this athlete to join their roster.
 *
 *  A club used to be able to add anyone straight to its roster. That mattered
 *  beyond manners: player-direct sponsorship packages are sold against roster
 *  membership, so a club could claim an athlete and monetise their audience
 *  while the athlete found out by looking at their own profile. Now it asks,
 *  and this is where the asking lands.
 */
function ClubInvitations() {
  const [invites, setInvites] = useState<ClubInvitation[] | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const toast = useToast()

  const load = () =>
    api.get<ClubInvitation[]>('/api/athlete/invitations').then(setInvites).catch(() => setInvites([]))
  useEffect(() => { void load() }, [])

  const respond = async (invite: ClubInvitation, action: 'accept' | 'decline') => {
    setBusy(invite.invitation_id)
    try {
      await api.post(`/api/athlete/invitations/${invite.invitation_id}/respond`, { action })
      toast(action === 'accept' ? `You are on ${invite.name}'s roster` : `Declined ${invite.name}`)
      await load()
    } finally {
      setBusy(null)
    }
  }

  if (!invites || invites.length === 0) return null

  return (
    <Section title="Club invitations"
             aside={<span className="meta">a club cannot add you without this</span>}>
      <div className="space-y-2">
        {invites.map((i) => (
          <div key={i.invitation_id} className="panel flex flex-wrap items-center gap-3 p-4">
            <div className="min-w-0">
              <div className="font-medium text-ink">{i.name}</div>
              <div className="text-xs text-ink-3">
                {i.sport} · {i.country}{i.position ? ` · as ${i.position}` : ''}
              </div>
            </div>
            <p className="meta max-w-md">
              Joining lets them build sponsorship packages around you, and vouch for you
              in admission. You can leave later.
            </p>
            <div className="ml-auto flex gap-2">
              <button className="btn-go px-3 py-1.5 text-xs" disabled={busy === i.invitation_id}
                      onClick={() => respond(i, 'accept')}>Accept</button>
              <button className="btn px-3 py-1.5 text-xs" disabled={busy === i.invitation_id}
                      onClick={() => respond(i, 'decline')}>Decline</button>
            </div>
          </div>
        ))}
      </div>
    </Section>
  )
}
