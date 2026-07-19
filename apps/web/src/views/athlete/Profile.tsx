import { useEffect, useState } from 'react'
import { LoadError, PageLoading, Section } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useToast } from '../../lib/toast'
import type { AthleteWorkspace } from '../../types'
import { DEAL_TYPES } from '../../types'

const TOPICS = ['fitness', 'training', 'running', 'basketball', 'football', 'tennis', 'cycling', 'endurance',
  'wellness', 'recovery', 'mindset', 'lifestyle', 'travel', 'outdoors', 'surfing', 'climbing', 'career', 'analytics']

export default function AthleteProfile() {
  const [form, setForm] = useState<AthleteWorkspace['editable'] | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const toast = useToast()

  useEffect(() => {
    api.get<AthleteWorkspace>('/api/athlete/workspace').then((ws) => setForm(ws.editable)).catch((e) => setError(errorText(e)))
  }, [])

  if (!form) return error ? <LoadError text={error} /> : <PageLoading />

  const set = (k: string, v: unknown) => setForm((f) => ({ ...f!, [k]: v }))
  const toggle = (list: string[], v: string) => (list.includes(v) ? list.filter((x) => x !== v) : [...list, v])

  const save = async () => {
    setError('')
    setStatus('')
    try {
      await api.put('/api/athlete/profile', form)
      toast('Profile saved')
    } catch (e) {
      setError(errorText(e))
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold text-mist-100">Profile</h1>
      <p className="mt-1 text-sm text-mist-400">
        Sponsors see this alongside your analytics. Set status to <span className="text-mist-200">listed</span> to appear in matching.
      </p>

      <Section title="Identity">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block"><span className="microcaps">Display name</span>
            <input className="field mt-1" value={form.display_name} onChange={(e) => set('display_name', e.target.value)} /></label>
          <label className="block"><span className="microcaps">Sport</span>
            <input className="field mt-1" value={form.sport} onChange={(e) => set('sport', e.target.value)} /></label>
          <label className="block"><span className="microcaps">Country</span>
            <input className="field mt-1" value={form.country} onChange={(e) => set('country', e.target.value)} /></label>
          <label className="block"><span className="microcaps">Region</span>
            <input className="field mt-1" value={form.region} onChange={(e) => set('region', e.target.value)} /></label>
        </div>
        <label className="mt-4 block"><span className="microcaps">Bio</span>
          <textarea className="field mt-1 min-h-24" value={form.bio} onChange={(e) => set('bio', e.target.value)} /></label>
        <label className="mt-4 block"><span className="microcaps">Career highlights (one per line)</span>
          <textarea className="field mt-1 min-h-20" value={form.career_highlights.join('\n')}
                    onChange={(e) => set('career_highlights', e.target.value.split('\n').filter(Boolean))} /></label>
      </Section>

      <Section title="Commercial">
        <label className="block max-w-xs"><span className="microcaps">Base rate (USD per engagement)</span>
          <input className="field mt-1 tnum" type="number" min={0} value={form.base_rate_usd}
                 onChange={(e) => set('base_rate_usd', Number(e.target.value))} /></label>
        <div className="mt-4">
          <div className="microcaps mb-2">Deal formats you offer</div>
          <div className="flex flex-wrap gap-2">
            {DEAL_TYPES.map((d) => (
              <button key={d.key} type="button"
                      onClick={() => set('deal_types', toggle(form.deal_types, d.key))}
                      className={`chip cursor-pointer ${form.deal_types.includes(d.key) ? 'border-pulse-500 text-mist-100' : ''}`}>
                {d.label}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4">
          <div className="microcaps mb-2">Content themes</div>
          <div className="flex flex-wrap gap-2">
            {TOPICS.map((t) => (
              <button key={t} type="button" onClick={() => set('topics', toggle(form.topics, t))}
                      className={`chip cursor-pointer ${form.topics.includes(t) ? 'border-pulse-500 text-mist-100' : ''}`}>
                {t}
              </button>
            ))}
          </div>
        </div>
      </Section>

      <Section title="Visibility">
        <div className="flex gap-2">
          {['draft', 'listed', 'hidden'].map((s) => (
            <button key={s} type="button" onClick={() => set('status', s)}
                    className={`btn capitalize ${form.status === s ? 'border-pulse-500 text-mist-100' : ''}`}>
              {s}
            </button>
          ))}
        </div>
      </Section>

      <div className="mt-8 flex items-center gap-3">
        <button className="btn-primary" onClick={save}>Save profile</button>
        {status && <span className="text-sm text-ok">{status}</span>}
        {error && <span className="text-sm text-danger">{error}</span>}
      </div>
    </div>
  )
}
