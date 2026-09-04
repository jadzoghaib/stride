import { ImagePlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, LoadError, PageHeader, PageLoading, Section } from '../../components/ui'
import { Cover } from '../../components/Cover'
import { api, errorText } from '../../lib/api'
import { COUNTRIES, REGIONS, SPORTS, withCurrent } from '../../lib/reference'
import { useToast } from '../../lib/toast'
import type { AthleteWorkspace } from '../../types'
import { DEAL_TYPES } from '../../types'

const TOPICS = ['fitness', 'training', 'running', 'basketball', 'football', 'tennis', 'cycling', 'endurance',
  'wellness', 'recovery', 'mindset', 'lifestyle', 'travel', 'outdoors', 'surfing', 'climbing', 'career', 'analytics']

export default function AthleteProfile() {
  const [form, setForm] = useState<AthleteWorkspace['editable'] | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<string | null>(null)
  const toast = useToast()

  useEffect(() => {
    api.get<AthleteWorkspace>('/api/athlete/workspace').then((ws) => setForm(ws.editable)).catch((e) => setError(errorText(e)))
  }, [])

  if (!form) return error ? <LoadError text={error} /> : <PageLoading />

  const set = (k: string, v: unknown) => setForm((f) => ({ ...f!, [k]: v }))

  /** Upload, then save the returned path straight away.
   *
   *  Not deferred to the Save button: a picture is the one field where the
   *  result is the feedback, and leaving it staged means a reader who uploads a
   *  photo, sees it appear, and navigates away has silently discarded it. The
   *  server hands back a path under our own media route, which is the only
   *  shape `PUT /api/athlete/profile` will accept for these two fields. */
  const putPhoto = async (field: 'avatar_url' | 'cover_url', file: File) => {
    setError('')
    setBusy(field)
    try {
      const { media_url } = await api.upload<{ media_url: string }>('/api/media', file)
      await api.put('/api/athlete/profile', { [field]: media_url })
      set(field, media_url)
      toast(field === 'avatar_url' ? 'Profile picture updated' : 'Cover updated')
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(null)
    }
  }

  const clearPhoto = async (field: 'avatar_url' | 'cover_url') => {
    setError('')
    try {
      await api.put('/api/athlete/profile', { [field]: '' })
      set(field, '')
      toast('Back to the drawn one')
    } catch (e) { setError(errorText(e)) }
  }
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
      <PageHeader
        eyebrow="Athlete"
        title="Profile"
        lede={
          <>
            Sponsors see this alongside your analytics. Set status to{' '}
            <span className="text-ink-2">listed</span> to appear in matching.
          </>
        }
      />

      {/* Photographs first: it is the part of the page a reader looks at, and
          the only part that is optional in the real sense — the drawn cover and
          avatar are a designed fallback, not a placeholder, so "no picture" is
          a finished state rather than an unfinished one. */}
      <Section title="Photographs"
               aside={<span className="meta">jpg, png, webp or gif · up to 8 MB</span>}>
        <div className="panel overflow-hidden">
          <div className="relative">
            <Cover name={form.display_name} src={form.cover_url} height="h-36" />
            <div className="absolute -bottom-8 left-5">
              <div className="rounded-full border-4 border-panel">
                <Avatar name={form.display_name} size={72} src={form.avatar_url} />
              </div>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2 px-5 pb-5 pt-11">
            <PhotoButton label={form.avatar_url ? 'Replace picture' : 'Upload picture'}
                         busy={busy === 'avatar_url'}
                         onPick={(f) => void putPhoto('avatar_url', f)} />
            {form.avatar_url && (
              <button className="btn px-3 py-1.5 text-xs"
                      onClick={() => void clearPhoto('avatar_url')}>Remove picture</button>
            )}
            <span className="mx-1 h-4 w-px bg-line" />
            <PhotoButton label={form.cover_url ? 'Replace cover' : 'Upload cover'}
                         busy={busy === 'cover_url'}
                         onPick={(f) => void putPhoto('cover_url', f)} />
            {form.cover_url && (
              <button className="btn px-3 py-1.5 text-xs"
                      onClick={() => void clearPhoto('cover_url')}>Remove cover</button>
            )}
          </div>
        </div>
        <p className="meta mt-2">
          This is exactly how the top of your public page looks. Removing a photograph goes back to
          the drawn one rather than leaving a blank.
        </p>
      </Section>

      <Section title="Identity">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block"><span className="cap">Display name</span>
            <input className="field mt-1" value={form.display_name} onChange={(e) => set('display_name', e.target.value)} /></label>
          <label className="block"><span className="cap">Sport</span>
            <select className="field mt-1" value={form.sport} onChange={(e) => set('sport', e.target.value)}>
              {withCurrent(SPORTS, form.sport).map((o) => <option key={o} value={o}>{o}</option>)}
            </select></label>
          <label className="block"><span className="cap">Country</span>
            <select className="field mt-1" value={form.country} onChange={(e) => set('country', e.target.value)}>
              {withCurrent(COUNTRIES, form.country).map((o) => <option key={o} value={o}>{o}</option>)}
            </select></label>
          <label className="block"><span className="cap">Region</span>
            <select className="field mt-1" value={form.region} onChange={(e) => set('region', e.target.value)}>
              {withCurrent(REGIONS, form.region).map((o) => <option key={o} value={o}>{o}</option>)}
            </select></label>
        </div>
        <label className="mt-4 block"><span className="cap">Bio</span>
          <textarea className="field mt-1 min-h-24" value={form.bio} onChange={(e) => set('bio', e.target.value)} /></label>
        <label className="mt-4 block"><span className="cap">Career highlights (one per line)</span>
          <textarea className="field mt-1 min-h-20" value={form.career_highlights.join('\n')}
                    onChange={(e) => set('career_highlights', e.target.value.split('\n').filter(Boolean))} /></label>
      </Section>

      <Section title="Commercial">
        <label className="block max-w-xs"><span className="cap">Base rate (EUR per engagement)</span>
          <input className="field mt-1 tnum" type="number" min={0} value={form.base_rate_eur}
                 onChange={(e) => set('base_rate_eur', Number(e.target.value))} /></label>
        <div className="mt-4">
          <div className="cap mb-2">Deal formats you offer</div>
          <div className="flex flex-wrap gap-2">
            {DEAL_TYPES.map((d) => (
              <button key={d.key} type="button"
                      onClick={() => set('deal_types', toggle(form.deal_types, d.key))}
                      className={`tag cursor-pointer ${form.deal_types.includes(d.key) ? 'border-accent text-ink' : ''}`}>
                {d.label}
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4">
          <div className="cap mb-2">Content themes</div>
          <div className="flex flex-wrap gap-2">
            {TOPICS.map((t) => (
              <button key={t} type="button" onClick={() => set('topics', toggle(form.topics, t))}
                      className={`tag cursor-pointer ${form.topics.includes(t) ? 'border-accent text-ink' : ''}`}>
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
                    className={`btn capitalize ${form.status === s ? 'border-accent text-ink' : ''}`}>
              {s}
            </button>
          ))}
        </div>
        {/* Eligibility left the primary nav when it became a step of signing up.
            It belongs here instead: this is the screen where an athlete notices
            they are Draft, and therefore the screen where they need the reason. */}
        <p className="meta mt-3">
          Listing also depends on your eligibility review —{' '}
          <Link to="/athlete/application" className="text-accent-ink underline underline-offset-2">
            see your application and its verdict
          </Link>
          .
        </p>
      </Section>

      <div className="mt-8 flex items-center gap-3">
        <button className="btn-go" onClick={save}>Save profile</button>
        {status && <span className="text-sm text-ok">{status}</span>}
        {error && <span className="text-sm text-critical">{error}</span>}
      </div>
    </div>
  )
}


/** A file picker that looks like the rest of the buttons.
 *
 *  A bare `<input type="file">` is unstyleable across browsers, so the input is
 *  hidden inside the label and the label carries the button's own classes —
 *  which keeps it keyboard-reachable and screen-reader-labelled, unlike the
 *  common trick of a button that clicks a hidden input through a ref. */
function PhotoButton({ label, busy, onPick }: {
  label: string
  busy: boolean
  onPick: (file: File) => void
}) {
  return (
    <label className={`btn cursor-pointer px-3 py-1.5 text-xs ${busy ? 'opacity-60' : ''}`}>
      <ImagePlus size={13} strokeWidth={1.9} />
      {busy ? 'Uploading…' : label}
      <input type="file" className="sr-only" accept="image/jpeg,image/png,image/webp,image/gif"
             disabled={busy}
             onChange={(e) => {
               const file = e.target.files?.[0]
               // Cleared so choosing the same file twice still fires a change.
               e.target.value = ''
               if (file) onPick(file)
             }} />
    </label>
  )
}
