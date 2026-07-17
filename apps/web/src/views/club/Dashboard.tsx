import { Plus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, EmptyNote, Section, Stat, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtDate, fmtMoney } from '../../lib/format'
import type { ClubWorkspace } from '../../types'

export default function ClubDashboard() {
  const [ws, setWs] = useState<ClubWorkspace | null>(null)
  const [error, setError] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [creatingPackage, setCreatingPackage] = useState(false)

  const load = () => api.get<ClubWorkspace>('/api/club/workspace').then(setWs).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [])

  const act = async (fn: () => Promise<unknown>) => {
    setError('')
    try {
      await fn()
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!ws) return <div className="text-mist-400">{error || 'Loading club workspace…'}</div>

  const activePackages = ws.packages.filter((p) => p.status === 'active')

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-mist-100">{ws.club.name}</h1>
        <span className="chip">{ws.club.sport}</span>
        <span className="chip">{ws.club.country}</span>
        <StatusChip status={ws.editable.status} />
        <Link to={`/clubs/${ws.club.slug}`} className="btn ml-auto px-3 py-1 text-xs">Public page</Link>
      </div>
      {ws.editable.status === 'draft' && (
        <div className="mt-3 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-sm text-warn">
          Your club is in draft — set it to listed below to appear in the directory.
        </div>
      )}
      {error && <div className="mt-4 rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>}

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <Stat label="Active sponsorship revenue" value={fmtMoney(ws.revenue_active)} sub="committed packages" />
        <Stat label="Roster" value={ws.roster.length} sub="active athletes" />
        <Stat label="Packages live" value={activePackages.length}
              sub={`${activePackages.filter((p) => p.package_type === 'player_direct').length} player-direct`} />
      </div>

      <Section title="Sponsorship packages"
               aside={<button className="btn px-3 py-1 text-xs" onClick={() => setCreatingPackage((v) => !v)}>
                 <Plus size={13} /> New package</button>}>
        {creatingPackage && (
          <PackageForm roster={ws.roster.map((m) => ({ slug: m.slug, name: m.display_name }))}
                       onDone={() => { setCreatingPackage(false); void load() }} />
        )}
        <table className="w-full text-sm">
          <thead>
            <tr>
              <th className="table-head">Package</th>
              <th className="table-head">Type</th>
              <th className="table-head">Player</th>
              <th className="table-head text-right">Price</th>
              <th className="table-head text-right">Backers</th>
              <th className="table-head">Status</th>
              <th className="table-head" />
            </tr>
          </thead>
          <tbody>
            {ws.packages.map((p) => (
              <tr key={p.id}>
                <td className="table-cell text-mist-100">{p.name}</td>
                <td className="table-cell">
                  <span className={`chip ${p.package_type === 'player_direct' ? 'border-pulse-500 text-mist-100' : ''}`}>
                    {p.package_type === 'player_direct' ? 'Player-direct' : 'Club'}
                  </span>
                </td>
                <td className="table-cell">{p.athlete_name ?? '—'}</td>
                <td className="table-cell tnum text-right">{fmtMoney(p.price_usd)}</td>
                <td className="table-cell tnum text-right">{p.active_backers}</td>
                <td className="table-cell"><StatusChip status={p.status} /></td>
                <td className="table-cell text-right">
                  {p.status === 'active' && (
                    <button className="btn px-2.5 py-1 text-xs"
                            onClick={() => act(() => api.post(`/api/club/packages/${p.id}/archive`))}>
                      Archive
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {ws.packages.length === 0 && <EmptyNote text="No packages yet — a package is what sponsors commit to." />}
      </Section>

      <Section title="Roster"
               aside={<button className="btn px-3 py-1 text-xs" onClick={() => setAddingMember((v) => !v)}>
                 <Plus size={13} /> Add athlete</button>}>
        {addingMember && <MemberForm onDone={() => { setAddingMember(false); void load() }} />}
        <div className="grid gap-2 md:grid-cols-2">
          {ws.roster.map((m) => (
            <div key={m.athlete_id} className="panel flex items-center gap-3 p-3">
              <Avatar name={m.display_name} size={36} />
              <div className="min-w-0">
                <Link to={`/athletes/${m.slug}`} className="text-sm font-medium text-mist-100 hover:text-pulse-400">
                  {m.display_name}
                </Link>
                <div className="text-xs text-mist-400">{m.position || m.sport} · joined {fmtDate(m.joined_at)}</div>
              </div>
              <button className="ml-auto text-mist-400 hover:text-danger" title="Remove from roster"
                      onClick={() => {
                        if (confirm(`Remove ${m.display_name}? Their player-direct packages will be archived.`))
                          void act(() => api.post(`/api/club/members/${m.athlete_id}/remove`))
                      }}>
                <X size={15} />
              </button>
            </div>
          ))}
        </div>
        {ws.roster.length === 0 && <EmptyNote text="No athletes on the roster yet — add athletes by their Stride handle." />}
      </Section>

      <Section title="Commitments">
        {ws.commitments.length === 0 ? (
          <EmptyNote text="No sponsor commitments yet. Sponsors back packages from your public page." />
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Sponsor</th>
                <th className="table-head">Package</th>
                <th className="table-head">Player</th>
                <th className="table-head text-right">Amount</th>
                <th className="table-head">Status</th>
                <th className="table-head">Since</th>
              </tr>
            </thead>
            <tbody>
              {ws.commitments.map((c) => (
                <tr key={c.id}>
                  <td className="table-cell text-mist-100">{c.org_name}</td>
                  <td className="table-cell">{c.package_name}</td>
                  <td className="table-cell">{c.athlete_name ?? '—'}</td>
                  <td className="table-cell tnum text-right">{fmtMoney(c.amount_usd)}</td>
                  <td className="table-cell"><StatusChip status={c.status} /></td>
                  <td className="table-cell text-xs text-mist-400">{fmtDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Club profile">
        <ProfileForm editable={ws.editable} onSaved={load} />
      </Section>
    </div>
  )
}

function MemberForm({ onDone }: { onDone: () => void }) {
  const [slug, setSlug] = useState('')
  const [position, setPosition] = useState('')
  const [error, setError] = useState('')
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/club/members', { athlete_slug: slug.trim(), position })
      onDone()
    } catch (err) {
      setError(errorText(err))
    }
  }
  return (
    <form onSubmit={submit} className="panel mb-3 flex flex-wrap items-end gap-3 border-pulse-500 p-4">
      <label className="block">
        <span className="microcaps">Athlete handle (slug)</span>
        <input className="field mt-1 w-56" required value={slug} onChange={(e) => setSlug(e.target.value)}
               placeholder="e.g. sofia-brandt" />
      </label>
      <label className="block">
        <span className="microcaps">Position / role</span>
        <input className="field mt-1 w-44" value={position} onChange={(e) => setPosition(e.target.value)} />
      </label>
      <button className="btn-primary">Add to roster</button>
      {error && <span className="text-sm text-danger">{error}</span>}
      <span className="w-full text-xs text-mist-400">Handles are visible on athlete profile pages in the directory.</span>
    </form>
  )
}

function PackageForm({ roster, onDone }: { roster: { slug: string; name: string }[]; onDone: () => void }) {
  const [form, setForm] = useState({
    name: '', description: '', package_type: 'club', price_usd: 10000,
    athlete_slug: roster[0]?.slug ?? '', perks: '',
  })
  const [error, setError] = useState('')
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/club/packages', {
        name: form.name, description: form.description, package_type: form.package_type,
        price_usd: form.price_usd,
        athlete_slug: form.package_type === 'player_direct' ? form.athlete_slug : null,
        perks: form.perks.split('\n').map((s) => s.trim()).filter(Boolean),
      })
      onDone()
    } catch (err) {
      setError(errorText(err))
    }
  }
  return (
    <form onSubmit={submit} className="panel mb-3 space-y-3 border-pulse-500 p-4">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block"><span className="microcaps">Package name</span>
          <input className="field mt-1" required minLength={3} value={form.name}
                 onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} /></label>
        <label className="block"><span className="microcaps">Price (USD)</span>
          <input className="field mt-1 tnum" type="number" min={1} value={form.price_usd}
                 onChange={(e) => setForm((f) => ({ ...f, price_usd: Number(e.target.value) }))} /></label>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block"><span className="microcaps">Type</span>
          <select className="field mt-1" value={form.package_type}
                  onChange={(e) => setForm((f) => ({ ...f, package_type: e.target.value }))}>
            <option value="club">Club package</option>
            <option value="player_direct">Player-direct (backs one roster athlete)</option>
          </select></label>
        {form.package_type === 'player_direct' && (
          <label className="block"><span className="microcaps">Roster athlete</span>
            <select className="field mt-1" value={form.athlete_slug}
                    onChange={(e) => setForm((f) => ({ ...f, athlete_slug: e.target.value }))}>
              {roster.map((m) => <option key={m.slug} value={m.slug}>{m.name}</option>)}
            </select></label>
        )}
      </div>
      <label className="block"><span className="microcaps">Description</span>
        <input className="field mt-1" value={form.description}
               onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} /></label>
      <label className="block"><span className="microcaps">Perks (one per line)</span>
        <textarea className="field mt-1 min-h-16" value={form.perks}
                  onChange={(e) => setForm((f) => ({ ...f, perks: e.target.value }))} /></label>
      {error && <div className="text-sm text-danger">{error}</div>}
      <button className="btn-primary">Publish package</button>
    </form>
  )
}

function ProfileForm({ editable, onSaved }: { editable: ClubWorkspace['editable']; onSaved: () => void }) {
  const [form, setForm] = useState(editable)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))
  const save = async () => {
    setError('')
    setStatus('')
    try {
      await api.put('/api/club/profile', form)
      setStatus('Saved.')
      onSaved()
    } catch (e) {
      setError(errorText(e))
    }
  }
  return (
    <div className="max-w-2xl">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block"><span className="microcaps">Club name</span>
          <input className="field mt-1" value={form.name} onChange={(e) => set('name', e.target.value)} /></label>
        <label className="block"><span className="microcaps">Sport</span>
          <input className="field mt-1" value={form.sport} onChange={(e) => set('sport', e.target.value)} /></label>
        <label className="block"><span className="microcaps">Country</span>
          <input className="field mt-1" value={form.country} onChange={(e) => set('country', e.target.value)} /></label>
        <label className="block"><span className="microcaps">Region</span>
          <input className="field mt-1" value={form.region} onChange={(e) => set('region', e.target.value)} /></label>
      </div>
      <label className="mt-4 block"><span className="microcaps">About the club</span>
        <textarea className="field mt-1 min-h-20" value={form.bio} onChange={(e) => set('bio', e.target.value)} /></label>
      <div className="mt-4 flex items-center gap-2">
        {['draft', 'listed', 'hidden'].map((s) => (
          <button key={s} type="button" onClick={() => set('status', s)}
                  className={`btn capitalize ${form.status === s ? 'border-pulse-500 text-mist-100' : ''}`}>
            {s}
          </button>
        ))}
        <button className="btn-primary ml-4" onClick={save}>Save</button>
        {status && <span className="text-sm text-ok">{status}</span>}
        {error && <span className="text-sm text-danger">{error}</span>}
      </div>
    </div>
  )
}
