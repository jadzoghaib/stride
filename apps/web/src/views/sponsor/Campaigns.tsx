import { Pencil, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Board } from '../../components/Board'
import { LoadError, PageLoading, EmptyNote, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useToast } from '../../lib/toast'
import { fmtMoney } from '../../lib/format'
import type { Campaign, Deal, Facets } from '../../types'
import { CATEGORIES, DEAL_TYPES, dealTypeLabel } from '../../types'

interface Workspace {
  // `website` was always in the payload — /api/sponsor/workspace returns the
  // whole row — and only missing from this declaration, so nothing could read it.
  org: { id: number; name: string; industry: string; website: string; regions: string[] }
  campaigns: Campaign[]
  deals: Deal[]
  club_commitments?: { id: number }[]
  spend_committed: number
  speed?: { median_hours: number | null; campaigns_measured: number; campaigns_without_offer: number }
}

/** Brief to first offer, in the coarsest unit that still says something. The
 *  agencies this competes with sell speed as a claim; a marketplace can show
 *  the clock instead. `null` stays a dash — no campaign has produced an offer,
 *  which is not the same statement as an instant one. */
const fmtWait = (hours: number | null | undefined) => {
  if (hours === null || hours === undefined) return '—'
  if (hours < 1) return '<1h'
  if (hours < 48) return `${Math.round(hours)}h`
  return `${Math.round(hours / 24)}d`
}

// Age buckets stay fixed: they are the demographic schema itself, not a list of
// what happens to exist. Countries and themes are derived — see /athletes/facets.
const AGE_BUCKETS = ['13-17', '18-24', '25-34', '35-44', '45-54', '55+']

export default function SponsorCampaigns() {
  const [ws, setWs] = useState<Workspace | null>(null)
  const [creating, setCreating] = useState(false)
  const [editing, setEditing] = useState<Campaign | null>(null)
  const [editingOrg, setEditingOrg] = useState(false)
  const [error, setError] = useState('')
  const toast = useToast()

  /* Closing is not deleting: the deals under a campaign are the sponsor's own
     record. A closed brief stops taking offers and can be reopened. */
  const setStatus = async (c: Campaign, status: 'active' | 'closed') => {
    setError('')
    try {
      await api.post(`/api/campaigns/${c.id}/status`, { status })
      toast(status === 'closed' ? `${c.name} closed` : `${c.name} reopened`)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  const load = () => api.get<Workspace>('/api/sponsor/workspace').then(setWs).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
  }, [])

  if (!ws) return error ? <LoadError text={error} /> : <PageLoading />

  const open = ws.deals.filter((d) => d.status === 'offered').length
  const answered = ws.deals.filter((d) => d.status === 'accepted' || d.status === 'declined')
  const accepted = answered.filter((d) => d.status === 'accepted').length

  return (
    <>
      <Board
        eyebrow="Sponsor"
        title={ws.org.name}
        tags={<span className="tag">{ws.org.industry}</span>}
        score={ws.spend_committed}
        scoreFormat={(n) => fmtMoney(Math.round(n))}
        scoreLabel="Committed spend"
        /* the rule reports the accept rate — the money figure is not a
           percentage of anything, so the rule has to measure something else */
        rulePct={answered.length ? (100 * accepted) / answered.length : 0}
        deltaNote={
          answered.length
            ? `${accepted} of ${answered.length} answered offers accepted`
            : 'no offers answered yet'
        }
        trendEmpty="Deals and club packages both count toward committed spend."
        figures={[
          { label: 'Active campaigns', value: ws.campaigns.filter((c) => c.status === 'active').length },
          { label: 'Open offers', value: open, to: '/sponsor/pipeline' },
          { label: 'Club packages', value: ws.club_commitments?.length ?? 0, to: '/sponsor/pipeline' },
          { label: 'Brief to first offer', value: fmtWait(ws.speed?.median_hours) },
        ]}
        footNote={
          ws.speed?.campaigns_measured
            ? `median over ${ws.speed.campaigns_measured} campaign${ws.speed.campaigns_measured === 1 ? '' : 's'}` +
              (ws.speed.campaigns_without_offer
                ? ` · ${ws.speed.campaigns_without_offer} still without an offer`
                : '')
            : 'no campaign has produced an offer yet'
        }
      />

      <div>
      <Section
        title="Organization"
        aside={
          <button className="btn px-3 py-1 text-xs" onClick={() => setEditingOrg((v) => !v)}>
            <Pencil size={12} /> {editingOrg ? 'Cancel' : 'Edit details'}
          </button>
        }
      >
        {editingOrg ? (
          <OrgForm org={ws.org} onDone={() => { setEditingOrg(false); toast('Organization updated'); void load() }} />
        ) : (
          <div className="panel flex flex-wrap items-baseline gap-x-5 gap-y-1 p-5">
            <span className="font-medium text-ink">{ws.org.name}</span>
            <span className="tag">{ws.org.industry || 'no industry set'}</span>
            {ws.org.website
              ? <a href={ws.org.website} target="_blank" rel="noreferrer noopener"
                   className="meta text-accent-ink hover:underline">{ws.org.website}</a>
              : <span className="meta">no website set</span>}
            <span className="meta ml-auto">
              {ws.org.regions.length ? ws.org.regions.join(' · ') : 'no regions set'}
            </span>
          </div>
        )}
      </Section>

      <Section
        title="Campaigns"
        aside={
          <button className="btn px-3 py-1 text-xs" onClick={() => setCreating((c) => !c)}>
            <Plus size={13} /> New campaign
          </button>
        }
      >
        {creating && (
          <CampaignForm onDone={() => { setCreating(false); toast('Campaign created'); void load() }}
                        onCancel={() => setCreating(false)} />
        )}
        {ws.campaigns.length === 0 && !creating && (
          <EmptyNote text="No campaigns yet. A campaign brief defines the audience you want — matching scores every listed athlete against it." />
        )}
        <div className="space-y-3">
          {ws.campaigns.map((c) => (
            /* Two destinations, because a campaign has two questions: who should
               be on it (matches) and how it is doing (analytics). The card was
               one link to the first, and the second had nowhere to be reached
               from. */
            <div key={c.id} className="panel p-5">
              <div className="flex flex-wrap items-center gap-3">
                <Link to={`/sponsor/campaigns/${c.id}`} className="font-medium text-ink hover:text-accent">
                  {c.name}
                </Link>
                <span className="tag">{c.category}</span>
                <StatusChip status={c.status} />
                <span className="ml-auto tnum text-sm text-ink-2">
                  {fmtMoney(c.budget_eur_min)} – {fmtMoney(c.budget_eur_max)}
                </span>
              </div>
              <p className="mt-1.5 text-sm text-ink-3">{c.objective}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
                {c.deal_types.map((t) => <span key={t} className="tag">{dealTypeLabel(t)}</span>)}
                {c.target_countries.length > 0 && <span className="tag">{c.target_countries.join(' · ')}</span>}
                {c.target_age_buckets.length > 0 && <span className="tag">ages {c.target_age_buckets.join(', ')}</span>}
              </div>
              {/* One destination, three tabs. Two buttons to two pages made the
                  card decide for you which question you had come with. */}
              <div className="mt-3 flex flex-wrap gap-2">
                <Link to={`/sponsor/campaigns/${c.id}`} className="btn px-3 py-1.5 text-xs">
                  Athletes
                </Link>
                <Link to={`/sponsor/campaigns/${c.id}?tab=pipeline`} className="btn px-3 py-1.5 text-xs">
                  Pipeline
                </Link>
                <Link to={`/sponsor/campaigns/${c.id}?tab=analytics`} className="btn px-3 py-1.5 text-xs">
                  Analytics
                </Link>
                <button className="btn ml-auto px-3 py-1.5 text-xs"
                        onClick={() => { setEditing(c); setCreating(false) }}>
                  <Pencil size={12} /> Edit
                </button>
                {c.status === 'closed' ? (
                  <button className="btn px-3 py-1.5 text-xs" onClick={() => setStatus(c, 'active')}>
                    Reopen
                  </button>
                ) : (
                  <button className="btn px-3 py-1.5 text-xs" onClick={() => setStatus(c, 'closed')}>
                    Close
                  </button>
                )}
              </div>
              {editing?.id === c.id && (
                <CampaignForm campaign={c}
                              onDone={() => { setEditing(null); toast('Campaign updated'); void load() }}
                              onCancel={() => setEditing(null)} />
              )}
            </div>
          ))}
        </div>
      </Section>
      </div>
    </>
  )
}

function CampaignForm({ campaign, onDone, onCancel }:
                      { campaign?: Campaign; onDone: () => void; onCancel: () => void }) {
  // Countries and themes come from what the directory actually contains, so a
  // sponsor can target the first athlete from a new country the day they list,
  // rather than when somebody remembers to add the code to an array here.
  const [facets, setFacets] = useState<Facets | null>(null)
  const [facetsFailed, setFacetsFailed] = useState(false)
  useEffect(() => {
    api.get<Facets>('/api/athletes/facets')
      .then(setFacets)
      .catch(() => setFacetsFailed(true))
  }, [])

  const [form, setForm] = useState({
    name: campaign?.name ?? '',
    objective: campaign?.objective ?? '',
    category: campaign?.category ?? CATEGORIES[0],
    deal_types: (campaign?.deal_types ?? []) as string[],
    budget_eur_min: campaign?.budget_eur_min ?? 2000,
    budget_eur_max: campaign?.budget_eur_max ?? 20000,
    target_age_buckets: (campaign?.target_age_buckets ?? []) as string[],
    target_countries: (campaign?.target_countries ?? []) as string[],
    target_topics: (campaign?.target_topics ?? []) as string[],
    // Carried, not edited. This form has never offered a gender control, so
    // an edit that omitted the field would have quietly blanked a targeting
    // dimension the brief was written with.
    target_genders: (campaign?.target_genders ?? []) as string[],
  })
  const [error, setError] = useState('')
  const toggle = (k: 'deal_types' | 'target_age_buckets' | 'target_countries' | 'target_topics', v: string) =>
    setForm((f) => ({ ...f, [k]: f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v] }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (campaign) await api.put(`/api/campaigns/${campaign.id}`, form)
      else await api.post('/api/campaigns', form)
      onDone()
    } catch (err) {
      setError(errorText(err))
    }
  }

  return (
    <form onSubmit={submit} className="panel mb-4 space-y-4 border-accent p-5">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block"><span className="cap">Campaign name</span>
          <input className="field mt-1" required minLength={3} value={form.name}
                 onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} /></label>
        <label className="block"><span className="cap">Category</span>
          <select className="field mt-1" value={form.category}
                  onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
            {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
          </select></label>
      </div>
      <label className="block"><span className="cap">Objective</span>
        <input className="field mt-1" value={form.objective}
               onChange={(e) => setForm((f) => ({ ...f, objective: e.target.value }))} /></label>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block"><span className="cap">Budget min (EUR)</span>
          <input className="field mt-1 tnum" type="number" min={0} value={form.budget_eur_min}
                 onChange={(e) => setForm((f) => ({ ...f, budget_eur_min: Number(e.target.value) }))} /></label>
        <label className="block"><span className="cap">Budget max (EUR)</span>
          <input className="field mt-1 tnum" type="number" min={0} value={form.budget_eur_max}
                 onChange={(e) => setForm((f) => ({ ...f, budget_eur_max: Number(e.target.value) }))} /></label>
      </div>
      {([
        ['Deal formats', 'deal_types', DEAL_TYPES.map((d) => d.key)],
        ['Target ages', 'target_age_buckets', AGE_BUCKETS],
        ['Target countries', 'target_countries', facets?.audience_countries ?? []],
        ['Target themes', 'target_topics', facets?.topics ?? []],
      ] as const).map(([label, key, options]) => (
        <div key={key}>
          <div className="cap mb-2">{label}</div>
          <div className="flex flex-wrap gap-2">
            {options.map((o) => (
              <button key={o} type="button" onClick={() => toggle(key, o)}
                      className={`tag cursor-pointer ${form[key].includes(o) ? 'border-accent text-ink' : ''}`}>
                {key === 'deal_types' ? dealTypeLabel(o) : o}
              </button>
            ))}
          </div>
        </div>
      ))}
      {error && <div className="text-sm text-critical">{error}</div>}
      {facetsFailed && (
        <p className="meta mb-2 text-critical">
          Targeting options could not be loaded. You can still create the campaign — it will
          match on budget and format only. There is no edit flow yet, so to add countries or
          themes you would have to create it again.
        </p>
      )}
      {/* Disabled only during the transient load. Gating on `facets` alone turned
          a missing secondary list into a permanent block on the core action;
          removing the guard entirely made the button clickable while it still
          read "Loading targeting…", which quietly created the untargeted
          campaign this whole change exists to prevent. */}
      <div className="flex items-center gap-3">
        <button className="btn-go" disabled={!facets && !facetsFailed}>
          {facets || facetsFailed ? 'Create campaign' : 'Loading targeting…'}</button>
        <button type="button" className="btn" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  )
}


/** The sponsor's own details. Athletes and clubs could always edit their public
 *  identity; a sponsor's was whatever the sign-up form guessed, and it sits on
 *  every offer they have ever sent. */
function OrgForm({ org, onDone }: { org: Workspace['org']; onDone: () => void }) {
  const [form, setForm] = useState({
    name: org.name, industry: org.industry ?? '', website: org.website ?? '',
    regions: org.regions ?? [],
  })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(''); setBusy(true)
    try {
      await api.put('/api/sponsor/org', form)
      onDone()
    } catch (err) {
      setError(errorText(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit} className="panel space-y-4 border-accent p-5">
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="cap">Organization name</span>
          <input className="field mt-1" required minLength={2} value={form.name}
                 onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} />
        </label>
        <label className="block">
          <span className="cap">Industry</span>
          <input className="field mt-1" value={form.industry}
                 onChange={(e) => setForm((f) => ({ ...f, industry: e.target.value }))} />
        </label>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block">
          <span className="cap">Website</span>
          <input className="field mt-1" type="url" placeholder="https://" value={form.website}
                 onChange={(e) => setForm((f) => ({ ...f, website: e.target.value }))} />
        </label>
        <label className="block">
          <span className="cap">Regions</span>
          <input className="field mt-1" placeholder="Europe, North America"
                 value={form.regions.join(', ')}
                 onChange={(e) => setForm((f) => ({
                   ...f, regions: e.target.value.split(',').map((r) => r.trim()).filter(Boolean),
                 }))} />
          <span className="meta mt-1 block">Comma separated.</span>
        </label>
      </div>
      {error && <div className="rounded border border-critical/40 bg-critical/10 px-3 py-2 text-sm text-critical">{error}</div>}
      <div className="flex justify-end">
        <button className="btn-go" disabled={busy}>{busy ? 'Saving…' : 'Save details'}</button>
      </div>
    </form>
  )
}
