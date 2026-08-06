import { Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { LoadError, PageLoading, EmptyNote, Section, Stat, StatusChip } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { fmtMoney } from '../../lib/format'
import type { Campaign, Deal } from '../../types'
import { CATEGORIES, DEAL_TYPES, dealTypeLabel } from '../../types'

interface Workspace {
  org: { id: number; name: string; industry: string; regions: string[] }
  campaigns: Campaign[]
  deals: Deal[]
  spend_committed: number
}

const AGE_BUCKETS = ['13-17', '18-24', '25-34', '35-44', '45-54', '55+']
const COUNTRY_CODES = ['US', 'GB', 'DE', 'FR', 'ES', 'BR', 'CA', 'AU', 'IN', 'MX']
const TOPICS = ['fitness', 'training', 'running', 'cycling', 'endurance', 'wellness', 'lifestyle', 'travel', 'analytics', 'mindset']

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

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold text-ink">{ws.org.name}</h1>
        <span className="tag">{ws.org.industry}</span>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <Stat label="Active campaigns" value={ws.campaigns.filter((c) => c.status === 'active').length} />
        <Stat label="Open offers" value={open} sub="awaiting athlete response — track in pipeline"
              to="/sponsor/pipeline" />
        <Stat label="Committed spend" value={fmtMoney(ws.spend_committed)} sub="deals + club packages"
              to="/sponsor/pipeline" />
      </div>

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
                  {fmtMoney(c.budget_usd_min)} – {fmtMoney(c.budget_usd_max)}
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
  )
}

function CampaignForm({ onDone }: { onDone: () => void }) {
  const [form, setForm] = useState({
    name: '', objective: '', category: CATEGORIES[0],
    deal_types: [] as string[], budget_usd_min: 2000, budget_usd_max: 20000,
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
        <label className="block"><span className="cap">Budget min (USD)</span>
          <input className="field mt-1 tnum" type="number" min={0} value={form.budget_usd_min}
                 onChange={(e) => setForm((f) => ({ ...f, budget_usd_min: Number(e.target.value) }))} /></label>
        <label className="block"><span className="cap">Budget max (USD)</span>
          <input className="field mt-1 tnum" type="number" min={0} value={form.budget_usd_max}
                 onChange={(e) => setForm((f) => ({ ...f, budget_usd_max: Number(e.target.value) }))} /></label>
      </div>
      {([
        ['Deal formats', 'deal_types', DEAL_TYPES.map((d) => d.key)],
        ['Target ages', 'target_age_buckets', AGE_BUCKETS],
        ['Target countries', 'target_countries', COUNTRY_CODES],
        ['Target themes', 'target_topics', TOPICS],
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
