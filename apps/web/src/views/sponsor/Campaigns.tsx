import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Board } from '../../components/Board'
import { LoadError, PageLoading, EmptyNote, Section, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney } from '../../lib/format'
import type { Campaign, Deal, Facets } from '../../types'
import { CATEGORIES, DEAL_TYPES, dealTypeLabel } from '../../types'

interface Workspace {
  org: { id: number; name: string; industry: string; regions: string[] }
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
  const [error, setError] = useState('')

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
        title="Campaigns"
        aside={
          <button className="btn px-3 py-1 text-xs" onClick={() => setCreating((c) => !c)}>
            <Plus size={13} /> New campaign
          </button>
        }
      >
        {creating && <CampaignForm onDone={() => { setCreating(false); void load() }} />}
        {ws.campaigns.length === 0 && !creating && (
          <EmptyNote text="No campaigns yet. A campaign brief defines the audience you want — matching scores every listed athlete against it." />
        )}
        <div className="space-y-3">
          {ws.campaigns.map((c) => (
            <Link key={c.id} to={`/sponsor/campaigns/${c.id}`} className="panel panel-hover block p-5">
              <div className="flex flex-wrap items-center gap-3">
                <span className="font-medium text-ink">{c.name}</span>
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
            </Link>
          ))}
        </div>
      </Section>
      </div>
    </>
  )
}

function CampaignForm({ onDone }: { onDone: () => void }) {
  // Countries and themes come from what the directory actually contains, so a
  // sponsor can target the first athlete from a new country the day they list,
  // rather than when somebody remembers to add the code to an array here.
  const [facets, setFacets] = useState<Facets | null>(null)
  useEffect(() => {
    api.get<Facets>('/api/athletes/facets').then(setFacets).catch(() => {})
  }, [])

  const [form, setForm] = useState({
    name: '', objective: '', category: CATEGORIES[0],
    deal_types: [] as string[], budget_eur_min: 2000, budget_eur_max: 20000,
    target_age_buckets: [] as string[], target_countries: [] as string[], target_topics: [] as string[],
  })
  const [error, setError] = useState('')
  const toggle = (k: 'deal_types' | 'target_age_buckets' | 'target_countries' | 'target_topics', v: string) =>
    setForm((f) => ({ ...f, [k]: f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v] }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/campaigns', form)
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
      <button className="btn-go">Create campaign</button>
    </form>
  )
}
