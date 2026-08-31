import { Plus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Board } from '../../components/Board'
import { LoadError, Modal, PageLoading, Avatar, EmptyNote, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { CONTENT_KINDS, CONTENT_TIERS } from '../../types'
import { useToast } from '../../lib/toast'
import { COUNTRIES, SPORTS, withCurrent } from '../../lib/reference'
import { openable } from '../../lib/url'
import { fmtDate, fmtMoney } from '../../lib/format'
import type { ClubWorkspace, ContentItem, RosterMember } from '../../types'

export default function ClubDashboard() {
  const [ws, setWs] = useState<ClubWorkspace | null>(null)
  const [error, setError] = useState('')
  const [addingMember, setAddingMember] = useState(false)
  const [creatingPackage, setCreatingPackage] = useState(false)
  const [removing, setRemoving] = useState<RosterMember | null>(null)
  const toast = useToast()

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

  if (!ws) return error ? <LoadError text={error} /> : <PageLoading />

  const activePackages = ws.packages.filter((p) => p.status === 'active')
  const backed = activePackages.filter((p) => p.active_backers > 0).length

  return (
    <>
      <Board
        eyebrow="Club"
        title={ws.club.name}
        tags={
          <>
            <span className="tag">{ws.club.sport}</span>
            <span className="tag">{ws.club.country}</span>
            <StatusChip status={ws.editable.status} />
          </>
        }
        score={ws.revenue_active}
        scoreFormat={(n) => fmtMoney(Math.round(n))}
        scoreLabel="Active sponsorship revenue"
        /* the rule reports inventory sold, not the revenue figure — a money
           headline is not a percentage of anything, so it needs its own source */
        rulePct={activePackages.length ? (100 * backed) / activePackages.length : 0}
        deltaNote={`${backed} of ${activePackages.length} live packages backed`}
        trendEmpty="Sponsors commit to packages from your public page."
        figures={[
          { label: 'Roster', value: ws.roster.length, to: '/club#roster' },
          { label: 'Packages live', value: activePackages.length, to: '/club#packages' },
          {
            label: 'Player-direct',
            value: activePackages.filter((p) => p.package_type === 'player_direct').length,
            to: '/club#packages',
          },
          { label: 'Commitments', value: ws.commitments.length, to: '/club#commitments' },
        ]}
        footNote={
          <Link to={`/clubs/${ws.club.slug}`} className="hover:text-ink-2">
            View public page →
          </Link>
        }
      />

      <div>
      {ws.editable.status === 'draft' && (
        <div className="mt-4 rounded border border-warn/45 bg-warn/10 px-3.5 py-2.5 text-sm text-warn">
          Your club is in draft — set it to listed below to appear in the directory.
        </div>
      )}
      {error && <div className="mt-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">{error}</div>}

      <Section title="Sponsorship packages" id="packages"
               aside={<button className="btn px-3 py-1 text-xs" onClick={() => setCreatingPackage((v) => !v)}>
                 <Plus size={13} /> New package</button>}>
        {creatingPackage && (
          <PackageForm roster={ws.roster.map((m) => ({ slug: m.slug, name: m.display_name }))}
                       onDone={() => { setCreatingPackage(false); toast('Package published'); void load() }} />
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
                <td className="table-cell text-ink">{p.name}</td>
                <td className="table-cell">
                  <span className={`tag ${p.package_type === 'player_direct' ? 'border-accent text-ink' : ''}`}>
                    {p.package_type === 'player_direct' ? 'Player-direct' : 'Club'}
                  </span>
                </td>
                <td className="table-cell">{p.athlete_name ?? '—'}</td>
                <td className="table-cell tnum text-right">{fmtMoney(p.price_eur)}</td>
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

      {/* "Invite", not "Add". A club used to write itself onto an athlete's
          record directly, which is how it could sell a player-direct package
          around someone who had never agreed to be on the roster. */}
      <Section title="Roster" id="roster"
               aside={<button className="btn px-3 py-1 text-xs" onClick={() => setAddingMember((v) => !v)}>
                 <Plus size={13} /> Invite athlete</button>}>
        {addingMember && <MemberForm onDone={() => { setAddingMember(false); toast('Invitation sent — it counts once they accept'); void load() }} />}
        <div className="grid gap-2 md:grid-cols-2">
          {ws.roster.map((m) => (
            <div key={m.athlete_id}
                 className={`panel flex items-center gap-3 p-3 ${
                   m.membership_status === 'invited' ? 'border-dashed opacity-80' : ''
                 }`}>
              <Avatar name={m.display_name} size={36} />
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <Link to={`/athletes/${m.slug}`} className="text-sm font-medium text-ink hover:text-accent">
                    {m.display_name}
                  </Link>
                  {m.membership_status === 'invited' && (
                    <span className="tag border-warn/50 text-warn">Invited</span>
                  )}
                </div>
                <div className="text-xs text-ink-3">
                  {m.position || m.sport} ·{' '}
                  {m.membership_status === 'invited'
                    ? `asked ${fmtDate(m.joined_at)} — waiting on them`
                    : `joined ${fmtDate(m.joined_at)}`}
                </div>
              </div>
              <button className="ml-auto text-ink-3 hover:text-critical"
                      title={`Remove ${m.display_name} from roster`}
                      aria-label={`Remove ${m.display_name} from roster`}
                      onClick={() => setRemoving(m)}>
                <X size={15} />
              </button>
            </div>
          ))}
        </div>
        {ws.roster.length === 0 && <EmptyNote text="Nobody on the roster yet — invite athletes by their Stride handle. They have to accept before packages can be built around them." />}
      </Section>

      <ClubContent />

      <Section title="Commitments" id="commitments">
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
                  <td className="table-cell text-ink">{c.org_name}</td>
                  <td className="table-cell">{c.package_name}</td>
                  <td className="table-cell">{c.athlete_name ?? '—'}</td>
                  <td className="table-cell tnum text-right">{fmtMoney(c.amount_eur)}</td>
                  <td className="table-cell"><StatusChip status={c.status} /></td>
                  <td className="table-cell text-xs text-ink-3">{fmtDate(c.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Club profile">
        <ProfileForm editable={ws.editable} onSaved={load} />
        {/* Eligibility left the nav when it became a step of signing up, which
            left "finish later" pointing at a page with no way back to it. A club
            cannot nominate until this is checked, so the route has to exist. */}
        <p className="meta mt-4">
          Nominating athletes requires a verified club —{' '}
          <Link to="/club/eligibility" className="text-accent-ink underline underline-offset-2">
            see your eligibility application and its verdict
          </Link>
          .
        </p>
      </Section>
      </div>

      {removing && (
        <Modal title={`Remove ${removing.display_name}?`} onClose={() => setRemoving(null)}>
          {(close) => (
            <>
              <p className="text-sm text-ink-2">
                They come off the active roster, and any player-direct package backing them is archived —
                ending the sponsor commitments attached to it.
              </p>
              <div className="mt-5 flex gap-2">
                <button
                  className="btn border-critical text-critical hover:border-critical hover:bg-critical/10 hover:text-critical"
                  onClick={() => {
                    const id = removing.athlete_id
                    close()
                    void act(() => api.post(`/api/club/members/${id}/remove`))
                  }}
                >
                  Remove from roster
                </button>
                <button className="btn" onClick={close}>
                  Keep on roster
                </button>
              </div>
            </>
          )}
        </Modal>
      )}
    </>
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
    <form onSubmit={submit} className="panel mb-3 flex flex-wrap items-end gap-3 border-accent p-4">
      <label className="block">
        <span className="cap">Athlete handle (slug)</span>
        <input className="field mt-1 w-56" required value={slug} onChange={(e) => setSlug(e.target.value)}
               placeholder="e.g. sofia-brandt" />
      </label>
      <label className="block">
        <span className="cap">Position / role</span>
        <input className="field mt-1 w-44" value={position} onChange={(e) => setPosition(e.target.value)} />
      </label>
      <button className="btn-go">Send invitation</button>
      {error && <span className="text-sm text-critical">{error}</span>}
      <span className="w-full text-xs text-ink-3">Handles are visible on athlete profile pages in the directory. The athlete has to accept before they join the roster — until they do, they are not a member and no player-direct package can be sold around them.</span>
    </form>
  )
}

function PackageForm({ roster, onDone }: { roster: { slug: string; name: string }[]; onDone: () => void }) {
  const [form, setForm] = useState({
    name: '', description: '', package_type: 'club', price_eur: 10000,
    athlete_slug: roster[0]?.slug ?? '', perks: '',
  })
  const [error, setError] = useState('')
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/club/packages', {
        name: form.name, description: form.description, package_type: form.package_type,
        price_eur: form.price_eur,
        athlete_slug: form.package_type === 'player_direct' ? form.athlete_slug : null,
        perks: form.perks.split('\n').map((s) => s.trim()).filter(Boolean),
      })
      onDone()
    } catch (err) {
      setError(errorText(err))
    }
  }
  return (
    <form onSubmit={submit} className="panel mb-3 space-y-3 border-accent p-4">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block"><span className="cap">Package name</span>
          <input className="field mt-1" required minLength={3} value={form.name}
                 onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} /></label>
        <label className="block"><span className="cap">Price (EUR)</span>
          <input className="field mt-1 tnum" type="number" min={1} value={form.price_eur}
                 onChange={(e) => setForm((f) => ({ ...f, price_eur: Number(e.target.value) }))} /></label>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block"><span className="cap">Type</span>
          <select className="field mt-1" value={form.package_type}
                  onChange={(e) => setForm((f) => ({ ...f, package_type: e.target.value }))}>
            <option value="club">Club package</option>
            <option value="player_direct">Player-direct (backs one roster athlete)</option>
          </select></label>
        {form.package_type === 'player_direct' && (
          <label className="block"><span className="cap">Roster athlete</span>
            <select className="field mt-1" value={form.athlete_slug}
                    onChange={(e) => setForm((f) => ({ ...f, athlete_slug: e.target.value }))}>
              {roster.map((m) => <option key={m.slug} value={m.slug}>{m.name}</option>)}
            </select></label>
        )}
      </div>
      <label className="block"><span className="cap">Description</span>
        <input className="field mt-1" value={form.description}
               onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} /></label>
      <label className="block"><span className="cap">Perks (one per line)</span>
        <textarea className="field mt-1 min-h-16" value={form.perks}
                  onChange={(e) => setForm((f) => ({ ...f, perks: e.target.value }))} /></label>
      {error && <div className="text-sm text-critical">{error}</div>}
      <button className="btn-go">Publish package</button>
    </form>
  )
}

function ProfileForm({ editable, onSaved }: { editable: ClubWorkspace['editable']; onSaved: () => void }) {
  const [form, setForm] = useState(editable)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }))
  const save = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setStatus('')
    try {
      await api.put('/api/club/profile', form)
      setStatus('Saved.')
      onSaved()
    } catch (err) {
      setError(errorText(err))
    }
  }
  return (
    <form onSubmit={save} className="max-w-2xl">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block"><span className="cap">Club name</span>
          <input className="field mt-1" value={form.name} onChange={(e) => set('name', e.target.value)} /></label>
        <label className="block"><span className="cap">Sport</span>
          <select className="field mt-1" value={form.sport} onChange={(e) => set('sport', e.target.value)}>
            {withCurrent(SPORTS, form.sport).map((o) => <option key={o} value={o}>{o}</option>)}
          </select></label>
        <label className="block"><span className="cap">Country</span>
          <select className="field mt-1" value={form.country} onChange={(e) => set('country', e.target.value)}>
            {withCurrent(COUNTRIES, form.country).map((o) => <option key={o} value={o}>{o}</option>)}
          </select></label>
        <label className="block"><span className="cap">Region</span>
          <input className="field mt-1" value={form.region} onChange={(e) => set('region', e.target.value)} /></label>
      </div>
      <label className="mt-4 block"><span className="cap">About the club</span>
        <textarea className="field mt-1 min-h-20" value={form.bio} onChange={(e) => set('bio', e.target.value)} /></label>
      <div className="mt-4 flex items-center gap-2">
        {['draft', 'listed', 'hidden'].map((s) => (
          <button key={s} type="button" onClick={() => set('status', s)}
                  className={`btn capitalize ${form.status === s ? 'border-accent text-ink' : ''}`}>
            {s}
          </button>
        ))}
        <button className="btn-go ml-4">Save</button>
        {status && <span className="text-sm text-ok">{status}</span>}
        {error && <span className="text-sm text-critical">{error}</span>}
      </div>
    </form>
  )
}

/** A club publishes too.
 *
 *  It has an audience no individual athlete has — its own followers, its
 *  members' families, its town — and its content is naturally event-shaped:
 *  academy days, open sessions, "train at our club". Those are the scarce,
 *  highest-margin kind, and they are also the club's answer to cold start: a
 *  club with thirty athletes can publish on day one while each of them is still
 *  building an audience.
 *
 *  Note the plan does not yet claim a euro of this. The financial model has
 *  three revenue lines and none of them is club fan revenue, so everything here
 *  is upside it does not count.
 */
/** A stored instant, as wall-clock time in *this* browser -- the only form a
 *  `datetime-local` input understands. `slice(0, 16)` was wrong in a way that
 *  looked right: it took the UTC digits and put them in a field that means
 *  local, so 09:00Z was shown as 09:00 and saved back as 09:00 local, moving
 *  the event by the reader's offset on every save. This is the exact inverse of
 *  the `toISOString()` on the way out, so the value round-trips unchanged. */
function toLocalInput(iso: string): string {
  const at = new Date(iso)
  if (Number.isNaN(at.getTime())) return ''
  return new Date(at.getTime() - at.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function ClubContent() {
  const [items, setItems] = useState<ContentItem[] | null>(null)
  const [form, setForm] = useState({ kind: 'post', title: '', body: '', min_tier: '', starts_at: '', location: '', capacity: '', external_url: '' })
  const [open, setOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const toast = useToast()

  const load = () => api.get<ContentItem[]>('/api/club/content').then(setItems).catch(() => setItems([]))
  useEffect(() => { void load() }, [])

  const scheduled = form.kind === 'session' || form.kind === 'event'
  const isProduct = form.kind === 'product'

  const reset = () => {
    setForm({ kind: 'post', title: '', body: '', min_tier: '', starts_at: '', location: '', capacity: '', external_url: '' })
    setEditingId(null)
    setOpen(false)
  }

  /** New or existing: same body, different address. Editing keeps the id, so a
   *  published item stays published and keeps its date. */
  const save = async () => {
    setError('')
    try {
      await api.post(editingId ? `/api/content/${editingId}` : '/api/club/content', {
        ...form,
        // a product is never locked and only a product carries a link
        min_tier: isProduct ? '' : form.min_tier,
        external_url: isProduct ? form.external_url : '',
        // only this browser knows its own offset; resolve the instant here
        starts_at: form.starts_at ? new Date(form.starts_at).toISOString() : '',
        capacity: form.capacity === '' ? null : Number(form.capacity),
      })
      toast(editingId ? 'Saved' : 'Saved as draft')
      reset()
      await load()
    } catch (e) { setError(errorText(e)) }
  }

  const edit = (i: ContentItem) => {
    setForm({
      kind: i.kind, title: i.title, body: i.body, min_tier: i.min_tier,
      starts_at: i.starts_at ? toLocalInput(i.starts_at) : '',
      location: i.location, capacity: i.capacity == null ? '' : String(i.capacity),
      external_url: i.external_url ?? '',
    })
    setEditingId(i.id)
    setOpen(true)
  }

  const publish = async (i: ContentItem) => {
    try { await api.post(`/api/content/${i.id}/publish`); toast(`“${i.title}” is live`); await load() }
    catch (e) { setError(errorText(e)) }
  }
  const remove = async (i: ContentItem) => {
    try { await api.del(`/api/content/${i.id}`); await load() } catch (e) { setError(errorText(e)) }
  }

  return (
    <Section title="Content" id="content"
             aside={<button className="btn px-3 py-1 text-xs"
                            onClick={() => { if (open) { reset() } else { setEditingId(null); setOpen(true) } }}>
               <Plus size={13} /> New</button>}>
      {error && <p className="mb-3 text-sm text-critical">{error}</p>}

      {open && (
        <div className="panel mb-3 space-y-3 p-4">
          <div className="grid gap-3 md:grid-cols-3">
            <label className="block"><span className="cap">Kind</span>
              <select className="field mt-1" value={form.kind}
                      onChange={(e) => setForm((f) => ({ ...f, kind: e.target.value }))}>
                {CONTENT_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select></label>
            <label className="block md:col-span-2"><span className="cap">Title</span>
              <input className="field mt-1" value={form.title}
                     onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} /></label>
          </div>
          <label className="block"><span className="cap">Body</span>
            <textarea className="field mt-1 min-h-[5rem]" value={form.body}
                      onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))} /></label>
          <div className="grid gap-3 md:grid-cols-4">
            {isProduct ? (
              <label className="block md:col-span-2"><span className="cap">Where it is sold *</span>
                <input className="field mt-1" value={form.external_url}
                       onChange={(e) => setForm((f) => ({ ...f, external_url: e.target.value }))}
                       placeholder="https://shop.example/club-scarf" />
                <span className="meta mt-1 block">Stride links to your store and never takes a cut, so a product is not locked.</span>
              </label>
            ) : (
              <label className="block"><span className="cap">Fans need</span>
                <select className="field mt-1" value={form.min_tier}
                        onChange={(e) => setForm((f) => ({ ...f, min_tier: e.target.value }))}>
                  {CONTENT_TIERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select></label>
            )}
            {scheduled && (
              <>
                <label className="block"><span className="cap">Starts</span>
                  <input className="field mt-1" type="datetime-local" value={form.starts_at}
                         onChange={(e) => setForm((f) => ({ ...f, starts_at: e.target.value }))} /></label>
                <label className="block"><span className="cap">Where</span>
                  <input className="field mt-1" value={form.location}
                         onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))} /></label>
                <label className="block"><span className="cap">Places</span>
                  <input className="field mt-1" type="number" min={1} value={form.capacity}
                         onChange={(e) => setForm((f) => ({ ...f, capacity: e.target.value }))} /></label>
              </>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button className="btn-go"
                    disabled={!form.title.trim() || (isProduct && !openable(form.external_url.trim()))}
                    onClick={save}>{editingId ? 'Save changes' : 'Save as draft'}</button>
            {editingId && <button className="btn" onClick={reset}>Cancel</button>}
          </div>
        </div>
      )}

      {!items || items.length === 0 ? (
        <EmptyNote text="Nothing published yet. A club's own audience is one no single athlete has, and open sessions are the kind fans pay most for." />
      ) : (
        // The same two surfaces the club's public page shows, in the same
        // order: what a fan buys sits above what a fan follows, because for a
        // club the open session is the product and the posts are the trailer.
        <div className="space-y-6">
          {[
            { label: 'Shop', rows: items.filter((i) => i.kind === 'course' || i.starts_at) },
            { label: 'Wall', rows: items.filter((i) => i.kind === 'post' && !i.part_of) },
          ].filter((g) => g.rows.length > 0).map((group) => (
            <div key={group.label}>
              <p className="cap mb-2 text-ink-3">{group.label}</p>
              <div className="space-y-2">
                {group.rows.map((i) => (
                  <div key={i.id} className="panel flex flex-wrap items-center gap-3 p-3">
                    <span className="cap w-16 shrink-0 text-ink-3">{i.kind}</span>
                    <span className="text-sm font-medium text-ink">{i.title}</span>
                    <span className="tag">{i.tier_label}</span>
                    {i.starts_at && (
                      <span className="meta">{new Date(i.starts_at).toLocaleDateString()} · {i.location || 'TBC'}</span>
                    )}
                    <div className="ml-auto flex items-center gap-2">
                      <span className={`tag ${i.status === 'published' ? 'border-ok/50 text-ok' : ''}`}>{i.status}</span>
                      {i.status === 'draft' && (
                        <button className="btn px-3 py-1 text-xs" onClick={() => publish(i)}>Publish</button>
                      )}
                      <button className="btn px-3 py-1 text-xs" onClick={() => edit(i)}>Edit</button>
                      <button className="btn px-3 py-1 text-xs" onClick={() => remove(i)}>Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </Section>
  )
}
