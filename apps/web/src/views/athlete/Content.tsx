/** Where an athlete puts things.
 *
 *  Four kinds, and the split that decides the whole layout is scarcity: a post
 *  or a course costs nothing to serve to one more fan, while a session or an
 *  event costs the athlete a Saturday. The scarce two therefore ask for a date,
 *  a place and a capacity, and the form only shows those fields when they mean
 *  something.
 *
 *  Nothing here charges money. The tier a fan would need is recorded and shown;
 *  there is no checkout, because there is no payments stack yet and pretending
 *  otherwise would be the one dishonest screen in the product.
 */
import { useEffect, useState } from 'react'
import { EmptyNote, LoadError, Modal, PageHeader, PageLoading, Section, Tabs } from '../../components/ui'
import { useNavigate } from 'react-router-dom'
import { api, errorText } from '../../lib/api'
import { useAuth } from '../../lib/auth'
import { openable } from '../../lib/url'
import { useToast } from '../../lib/toast'
import type { ContentItem } from '../../types'
import { CONTENT_KINDS, CONTENT_LABELS, CONTENT_TIERS, SCHEDULED_KINDS } from '../../types'

const BLANK = {
  kind: 'post', title: '', body: '', min_tier: '', label: '', sponsor_name: '',
  part_of: null as number | null, position: '' as string,
  starts_at: '', location: '', capacity: '' as string, external_url: '',
  media_url: '', media_kind: '' as '' | 'image' | 'video', options: ['', ''] as string[],
}

export default function AthleteContent() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const [items, setItems] = useState<ContentItem[] | null>(null)
  const [error, setError] = useState('')
  const [composing, setComposing] = useState(false)
  const [tab, setTab] = useState<'wall' | 'shop'>('wall')
  const [editing, setEditing] = useState<ContentItem | null>(null)
  const toast = useToast()

  const load = () =>
    api.get<ContentItem[]>('/api/athlete/content').then(setItems).catch((e) => setError(errorText(e)))
  useEffect(() => { void load() }, [])

  const publish = async (item: ContentItem) => {
    try {
      await api.post(`/api/content/${item.id}/publish`)
      toast(`“${item.title}” is live`)
      await load()
    } catch (e) { setError(errorText(e)) }
  }

  const remove = async (item: ContentItem) => {
    try {
      await api.del(`/api/content/${item.id}`)
      toast(`Deleted “${item.title}”`)
      await load()
    } catch (e) { setError(errorText(e)) }
  }

  if (!items) return error ? <LoadError text={error} /> : <PageLoading />

  // The same two surfaces a fan sees, in the same words. What you manage and
  // what they meet should not be different shapes with different names.
  const courses = items.filter((i) => i.kind === 'course')
  const partsOf = (id: number) =>
    items.filter((i) => i.part_of === id).sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
  const posts = items.filter((i) => i.kind === 'post' && !i.part_of)
  const dated = items.filter((i) => i.starts_at && i.kind !== 'post')
  const published = items.filter((i) => i.status === 'published').length

  return (
    <div>
      <PageHeader
        eyebrow="Athlete"
        title="Content"
        lede="Two surfaces, and a fan meets them differently. Your wall is what they follow: posts, some free, some behind a tier, mixed in with what you already post on your own platforms. Your shop is what they buy — a course, a session, a day out with you."
        aside={<span className="meta">{published} published · {items.length - published} draft</span>}
      />

      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      {/* Edit, or see it the way a visitor does. Two modes of the same page:
          everything below is the management view, and the switch hands you the
          real public profile with the panels you only get because it is yours
          taken out of it. */}
      {me?.athlete_profile?.slug && (
        <div className="mb-5 max-w-xs">
          <Tabs
            active="edit"
            tabs={[{ key: 'edit', label: 'Edit' }, { key: 'public', label: 'Public view' }]}
            onChange={(k) => {
              if (k === 'public') navigate(`/athletes/${me.athlete_profile!.slug}?preview=1`)
            }}
          />
        </div>
      )}

      <div className="mb-5 flex items-center gap-3">
        <div className="flex-1">
          <Tabs
            active={tab}
            onChange={setTab}
            tabs={[
              { key: 'wall', label: 'Wall', count: posts.length },
              { key: 'shop', label: 'Shop', count: courses.length + dated.length },
            ]}
          />
        </div>
        <button className="btn-go px-3 py-2 text-xs" onClick={() => setComposing(true)}>+ New</button>
      </div>

      {tab === 'wall' ? (
        posts.length === 0 ? (
          <EmptyNote text="Nothing from you yet — your wall already shows your recent platform posts, so it is not empty to a visitor." />
        ) : (
          <div className="space-y-2">
            {posts.map((i) => (
              <div key={i.id} className="panel p-4">
                <Row item={i} onPublish={publish} onEdit={setEditing} onDelete={remove} />
              </div>
            ))}
          </div>
        )
      ) : (
        <div className="space-y-6">
          <Section title="Sessions & events">
            {dated.length === 0 ? (
              <EmptyNote text="Nothing dated yet. A session or an event costs you a day, which is why it sits in the top tier and why it needs a date, a place and a number of places." />
            ) : (
              <div className="space-y-2">
                {dated.map((i) => (
                  <div key={i.id} className="panel p-4">
                    <Row item={i} onPublish={publish} onEdit={setEditing} onDelete={remove} />
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title="Courses">
            {courses.length === 0 ? (
              <EmptyNote text="No courses yet. A course holds an ordered series — a twelve-week block, a technique series — and its parts inherit nothing, so each can sit at its own tier." />
            ) : (
              <div className="space-y-3">
                {courses.map((c) => (
                  <div key={c.id} className="panel p-4">
                    <Row item={c} onPublish={publish} onEdit={setEditing} onDelete={remove} />
                    <div className="mt-3 space-y-1.5 border-l border-line pl-4">
                      {partsOf(c.id).length === 0 ? (
                        <p className="meta">No parts yet.</p>
                      ) : (
                        partsOf(c.id).map((part) => (
                          <Row key={part.id} item={part} onPublish={publish} onEdit={setEditing} onDelete={remove} compact />
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>
        </div>
      )}

      {(composing || editing) && (
        // keyed so switching from one item to another remounts the form rather
        // than leaving the previous item's values in it
        <Compose key={editing ? `edit-${editing.id}` : 'new'}
                 courses={courses}
                 editing={editing}
                 onClose={() => { setComposing(false); setEditing(null) }}
                 onDone={() => { setComposing(false); setEditing(null); void load() }} />
      )}
    </div>
  )
}

function Row({ item, onPublish, onEdit, onDelete, compact = false }: {
  item: ContentItem
  onPublish: (i: ContentItem) => void
  onEdit: (i: ContentItem) => void
  onDelete: (i: ContentItem) => void
  compact?: boolean
}) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="cap w-16 shrink-0 text-ink-3">{item.kind}</span>
      <span className={compact ? 'text-sm text-ink-2' : 'font-medium text-ink'}>{item.title}</span>
      {item.label === 'sponsored' && (
        <span className="tag tag-warn">Sponsored · {item.sponsor_name}</span>
      )}
      {item.label === 'highlighted' && <span className="tag tag-accent">Highlighted</span>}
      <span className="tag">{item.tier_label}</span>
      {item.starts_at && (
        <span className="meta">{new Date(item.starts_at).toLocaleDateString()} · {item.location || 'TBC'}
          {item.capacity ? ` · ${item.capacity} places` : ''}</span>
      )}
      <div className="ml-auto flex items-center gap-2">
        <span className={`tag ${item.status === 'published' ? 'border-ok/50 text-ok' : ''}`}>
          {item.status}
        </span>
        {item.status === 'draft' && (
          <button className="btn px-3 py-1 text-xs" onClick={() => onPublish(item)}>Publish</button>
        )}
        <button className="btn px-3 py-1 text-xs" onClick={() => onEdit(item)}>Edit</button>
        <button className="btn px-3 py-1 text-xs" onClick={() => onDelete(item)}>Delete</button>
      </div>
    </div>
  )
}

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

/** An existing item, in the shape the form holds. `datetime-local` wants
 *  `YYYY-MM-DDTHH:mm` and the API returns an ISO instant, so the tail is cut
 *  off rather than parsed -- the value round-trips through the same field it
 *  came from. */
function toForm(item: ContentItem): typeof BLANK {
  return {
    kind: item.kind,
    title: item.title,
    body: item.body,
    min_tier: item.min_tier,
    label: item.label,
    sponsor_name: item.sponsor_name,
    part_of: item.part_of,
    position: item.position == null ? '' : String(item.position),
    starts_at: item.starts_at ? toLocalInput(item.starts_at) : '',
    location: item.location,
    capacity: item.capacity == null ? '' : String(item.capacity),
    external_url: item.external_url ?? '',
    media_url: item.media_url ?? '',
    media_kind: item.media_kind ?? '',
    options: item.poll?.options.map((o) => o.label) ?? ['', ''],
  }
}

function Compose({ courses, editing, onClose, onDone }: {
  courses: ContentItem[]
  editing: ContentItem | null
  onClose: () => void
  onDone: () => void
}) {
  const [form, setForm] = useState(() => (editing ? toForm(editing) : BLANK))
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const set = (k: keyof typeof BLANK, v: string | number | null) =>
    setForm((f) => ({ ...f, [k]: v }))
  const scheduled = SCHEDULED_KINDS.includes(form.kind as never)
  const isProduct = form.kind === 'product'
  const isPoll = form.kind === 'poll'

  const submit = async (close: () => void) => {
    setBusy(true)
    setError('')
    try {
      // Same body either way; only the address differs. Editing keeps the id,
      // which is what a course part hangs off and what a published_at belongs
      // to -- delete-and-recreate would lose both.
      await api.post(editing ? `/api/content/${editing.id}` : '/api/athlete/content', {
        ...form,
        // the server refuses a tier on a product and a link on anything else;
        // send the shape it expects rather than let a stale field 422 them
        min_tier: form.kind === 'product' ? '' : form.min_tier,
        external_url: form.kind === 'product' ? form.external_url : '',
        media_url: form.kind === 'product' ? '' : form.media_url,
        media_kind: form.kind === 'product' ? '' : form.media_kind,
        options: form.kind === 'poll' ? form.options.filter((o) => o.trim()) : [],
        // a datetime-local value is wall-clock time in this browser's zone, and
        // only this browser knows that zone -- so the instant is resolved here
        starts_at: form.starts_at ? new Date(form.starts_at).toISOString() : '',
        position: form.position === '' ? null : Number(form.position),
        capacity: form.capacity === '' ? null : Number(form.capacity),
      })
      close()
      onDone()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={editing ? `Edit ${editing.kind}` : 'New content'} onClose={onClose} wide>
      {(close) => (
        <div className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block"><span className="cap">Kind</span>
              <select className="field mt-1" value={form.kind} onChange={(e) => set('kind', e.target.value)}>
                {CONTENT_KINDS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
              <span className="meta mt-1 block">
                {isProduct
                  ? 'Sold on your own store. Stride links to it and never takes a cut, so it is not locked.'
                  : scheduled
                    ? 'Scarce: it costs you a day, so it is priced like one.'
                    : 'Unlimited: costs nothing to serve to one more fan.'}
              </span>
            </label>
            {isProduct ? (
              <label className="block"><span className="cap">Where it is sold *</span>
                <input className="field mt-1" value={form.external_url}
                       onChange={(e) => set('external_url', e.target.value)}
                       placeholder="https://your-shop.myshopify.com/products/..." />
                <span className="meta mt-1 block">
                  Shopify, Amazon, your own store — wherever the checkout already is.
                </span>
              </label>
            ) : (
              <label className="block"><span className="cap">Fans need</span>
                <select className="field mt-1" value={form.min_tier} onChange={(e) => set('min_tier', e.target.value)}>
                  {CONTENT_TIERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </label>
            )}
          </div>

          <label className="block"><span className="cap">Title</span>
            <input className="field mt-1" value={form.title} onChange={(e) => set('title', e.target.value)} />
          </label>

          {/* Media by link rather than upload: no storage stack is invented
              here, and a pasted URL is honest about where the file lives. */}
          {!isProduct && (
            <div className="grid gap-4 md:grid-cols-[1fr_10rem]">
              <label className="block"><span className="cap">Picture or clip (optional)</span>
                <input className="field mt-1" type="file" accept="image/*,video/*"
                       onChange={async (e) => {
                         const chosen = e.target.files?.[0]
                         if (!chosen) return
                         setUploading(true)
                         setError('')
                         try {
                           const done = await api.upload<{ media_url: string; media_kind: string }>(
                             '/api/media', chosen)
                           set('media_url', done.media_url)
                           set('media_kind', done.media_kind)
                         } catch (err) {
                           setError(errorText(err))
                         } finally {
                           setUploading(false)
                         }
                       }} />
                <span className="meta mt-1 block">
                  {uploading ? 'Uploading…'
                    : form.media_url ? 'Attached.'
                    : 'JPEG, PNG, WebP, GIF, MP4 or WebM, up to 8 MB.'}
                </span>
              </label>
              <label className="block"><span className="cap">Attached</span>
                <div className="field mt-1 truncate text-ink-3">
                  {form.media_url ? `${form.media_kind} · ${form.media_url.split('/').pop()}` : 'nothing yet'}
                </div>
                {form.media_url && (
                  <button type="button" className="btn mt-2 px-3 py-1 text-xs"
                          onClick={() => { set('media_url', ''); set('media_kind', '') }}>
                    Remove
                  </button>
                )}
              </label>
            </div>
          )}

          {isPoll && (
            <div className="space-y-2">
              <span className="cap">Answers</span>
              {form.options.map((o, i) => (
                <input key={i} className="field" value={o} placeholder={`Option ${i + 1}`}
                       onChange={(e) => setForm((f) => ({
                         ...f, options: f.options.map((x, j) => (j === i ? e.target.value : x)) }))} />
              ))}
              {form.options.length < 6 && (
                <button type="button" className="btn px-3 py-1 text-xs"
                        onClick={() => setForm((f) => ({ ...f, options: [...f.options, ''] }))}>
                  + Another answer
                </button>
              )}
              <span className="meta block">Two at least. Results are public from the start.</span>
            </div>
          )}

          <label className="block"><span className="cap">Body</span>
            <textarea className="field mt-1 min-h-[7rem]" value={form.body}
                      onChange={(e) => set('body', e.target.value)} />
            <span className="meta mt-1 block">
              {isProduct
                ? 'What it is. A product is never locked, so this is always visible.'
                : 'This is the part a locked item withholds. Everything else stays visible, so a fan can decide whether to pay.'}
            </span>
          </label>

          {scheduled && (
            <div className="grid gap-4 md:grid-cols-3">
              <label className="block"><span className="cap">Starts</span>
                <input className="field mt-1" type="datetime-local" value={form.starts_at}
                       onChange={(e) => set('starts_at', e.target.value)} />
              </label>
              <label className="block"><span className="cap">Where</span>
                <input className="field mt-1" value={form.location}
                       onChange={(e) => set('location', e.target.value)} />
              </label>
              <label className="block"><span className="cap">Places</span>
                <input className="field mt-1" type="number" min={1} value={form.capacity}
                       onChange={(e) => set('capacity', e.target.value)} />
              </label>
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <label className="block"><span className="cap">Label</span>
              <select className="field mt-1" value={form.label} onChange={(e) => set('label', e.target.value)}>
                {CONTENT_LABELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </label>
            {form.label === 'sponsored' && (
              <label className="block"><span className="cap">Sponsor *</span>
                <input className="field mt-1" value={form.sponsor_name}
                       onChange={(e) => set('sponsor_name', e.target.value)} />
                <span className="meta mt-1 block">Required. A disclosure that does not name the advertiser is not a disclosure.</span>
              </label>
            )}
          </div>

          {form.kind !== 'course' && courses.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              <label className="block"><span className="cap">Part of a course</span>
                <select className="field mt-1" value={form.part_of ?? ''}
                        onChange={(e) => set('part_of', e.target.value ? Number(e.target.value) : null)}>
                  <option value="">Standalone</option>
                  {courses.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
                </select>
              </label>
              {form.part_of && (
                <label className="block"><span className="cap">Position</span>
                  <input className="field mt-1" type="number" min={0} value={form.position}
                         onChange={(e) => set('position', e.target.value)} />
                </label>
              )}
            </div>
          )}

          {error && <p className="text-sm text-critical">{error}</p>}

          <div className="flex items-center gap-3">
            <button className="btn-go"
                    disabled={busy || uploading || !form.title.trim()
                              || (isProduct && !openable(form.external_url.trim()))}
                    onClick={() => submit(close)}>
              {busy ? 'Saving…' : editing ? 'Save changes' : 'Save as draft'}
            </button>
            <button className="btn" onClick={close}>Cancel</button>
            <span className="meta">
              {editing
                ? 'Saving does not publish or unpublish — that stays a separate decision.'
                : 'Drafts are private until you publish them.'}
            </span>
          </div>
        </div>
      )}
    </Modal>
  )
}
