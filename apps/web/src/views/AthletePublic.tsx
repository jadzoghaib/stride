/** An athlete, as a creator page.
 *
 *  The shape is the one every subscription platform has converged on, because
 *  it answers a reader's questions in the order they ask them: who is this
 *  (cover, avatar, name), what can I do about it (subscribe, message, follow),
 *  how big are they (audience), and then the work itself behind tabs.
 *
 *  What differs here is what a fan is *not* shown. The rate card and the
 *  marketability score are absent from the payload for anyone who is not
 *  buying the athlete's audience, so the sponsor-facing panels simply do not
 *  render — a fan gets the person, a sponsor gets the evidence, from the same
 *  URL.
 */
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AudiencePanel } from '../components/charts'
import { Shop, Wall } from '../components/content'
import { Cover } from '../components/Cover'
import {
  Avatar, DimensionGrid, EmptyNote, LoadError, MessageButton, PageLoading, Section, Tabs,
} from '../components/ui'
import { api, errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { fmtMoney, fmtNum } from '../lib/format'
import type { AthletePublic as Athlete, ContentItem, NewsItem } from '../types'
import { dealTypeLabel } from '../types'

type Tab = 'posts' | 'shop' | 'memberships' | 'wall'

/** The reference product offers All / Locked / Purchased / unlocked / Free.
 *  Four of those five are states we actually have; "Purchased" is not, because
 *  it means a single item bought on its own and there is no per-item purchase
 *  here — only a subscription. Offering it would be a filter that could never
 *  match anything. */
type Filter = 'all' | 'free' | 'unlocked' | 'locked'

/** What a membership is meant to cost. The plan prices three tiers; the demo
 *  charges nothing, and saying so on the card is better than a price that does
 *  not apply or a blank where the offer should be. */
const MEMBERSHIP = {
  name: 'Insider',
  price: '€9.99',
  perks: [
    'Everything marked subscribers-only, the moment it goes up',
    'Sessions and courses at member rates',
    'Message them directly',
  ],
}

export default function AthletePublicView() {
  const { slug } = useParams()
  const { me } = useAuth()
  const [a, setA] = useState<Athlete | null>(null)
  const [content, setContent] = useState<ContentItem[] | null>(null)
  const [news, setNews] = useState<NewsItem[]>([])
  const [tab, setTab] = useState<Tab>('posts')
  const [wall, setWall] = useState<FanPost[]>([])
  const [draft, setDraft] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Athlete>(`/api/athletes/${slug}`).then(setA).catch((e) => setError(errorText(e)))
    api.get<ContentItem[]>(`/api/athletes/${slug}/content`).then(setContent).catch(() => setContent([]))
    api.get<NewsItem[]>(`/api/athletes/${slug}/news`).then(setNews).catch(() => setNews([]))
    api.get<FanPost[]>(`/api/athletes/${slug}/wall-posts`).then(setWall).catch(() => setWall([]))
  }, [slug])

  const canRelate = !!me && ['athlete', 'fan', 'sponsor'].includes(me.role)

  const relate = async (kind: 'follow' | 'subscribe', on: boolean) => {
    if (!a) return
    const path = kind === 'follow' ? `/api/follows/${a.id}` : `/api/subscriptions/athlete/${a.id}`
    try {
      await (on ? api.del(path) : api.post(path))
      setA((prev) => prev && {
        ...prev,
        [kind === 'follow' ? 'following' : 'subscribed']: !on,
        followers: kind === 'follow' ? (prev.followers ?? 0) + (on ? -1 : 1) : prev.followers,
        subscribers: kind === 'subscribe' ? (prev.subscribers ?? 0) + (on ? -1 : 1) : prev.subscribers,
      })
      // subscribing changes what is readable, so the wall has to be re-read
      if (kind === 'subscribe') {
        setContent(await api.get<ContentItem[]>(`/api/athletes/${slug}/content`))
      }
    } catch (e) { setError(errorText(e)) }
  }

  const vote = async (item: ContentItem, optionId: number) => {
    try {
      const poll = await api.post<ContentItem['poll']>(`/api/content/${item.id}/vote/${optionId}`)
      setContent((list) => list?.map((c) => (c.id === item.id ? { ...c, poll } : c)) ?? null)
    } catch (e) { setError(errorText(e)) }
  }

  const items = useMemo(() => content ?? [], [content])
  const posts = items.filter((i) => (i.kind === 'post' || i.kind === 'poll') && !i.part_of)
  const shop = items.filter((i) => i.kind === 'course' || i.kind === 'product' || i.starts_at)
  const shown = useMemo(() => {
    // "Free" and "unlocked" are both readable, and telling them apart is the
    // point: one is open to everybody, the other is open because you pay.
    if (filter === 'free') return items.filter((i) => !i.min_tier)
    if (filter === 'unlocked') return items.filter((i) => i.min_tier && !i.locked)
    if (filter === 'locked') return items.filter((i) => i.locked)
    return items
  }, [items, filter])
  /** Everything a visitor can see on the Posts tab: what the athlete published
   *  in Stride, plus what they published on their own platforms.
   *
   *  The strip used to count only the first and the tab counted both, so the
   *  page showed "4 posts" directly above "POSTS 24" — two true numbers, six
   *  inches apart, labelled the same thing. A reader cannot tell that one means
   *  "authored here" and the other "in this feed", and does not care: they are
   *  all posts by this athlete, and the free/locked split is the distinction
   *  that actually matters, which the chips below already make. */
  const feedCount = posts.length + news.length
  //: Every content type the connectors produce is visual — video, reel, short,
  //  image, carousel — because Instagram, TikTok and YouTube are visual
  //  platforms. Listing 'video' and 'image' therefore silently dropped reels
  //  and shorts. Excluding a text type instead names the case that would not
  //  count, rather than trying to enumerate every case that would.
  const mediaCount = items.filter((i) => i.has_media || i.media_url).length
    + news.filter((n) => n.content_type !== 'text').length

  if (!a) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div className="min-w-0">
        {/* ── who this is ───────────────────────────────────────────────── */}
        <div className="overflow-hidden rounded-card border border-line bg-panel">
          <Cover name={a.display_name} />

          <div className="px-5 pb-5">
            {/* the avatar rides the cover's edge, which is what makes the
                header read as one object rather than two stacked blocks */}
            {/* relative + z: the negative margin lifts the avatar into the
                cover, but without a stacking context the cover paints over it
                and the face is half a circle. */}
            <div className="relative z-10 -mt-12 mb-3 w-fit rounded-full ring-4 ring-panel">
              <Avatar name={a.display_name} size={92} />
            </div>

            <div className="flex flex-wrap items-start gap-3">
              <div className="min-w-0">
                <h1 className="font-display text-[30px] font-bold leading-none text-ink">
                  {a.display_name}
                </h1>
                <p className="meta mt-1">@{a.slug}</p>
              </div>
              {a.status === 'listed' && (
                <span className="tag border-ok/50 text-ok">Verified athlete</span>
              )}
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {canRelate ? (
                <>
                  <button className={a.subscribed ? 'btn border-accent text-ink' : 'btn-go'}
                          onClick={() => relate('subscribe', !!a.subscribed)}>
                    {a.subscribed ? 'Subscribed' : 'Subscribe'}
                  </button>
                  {a.can_message && <MessageButton to={{ athlete: a.slug }} name={a.display_name} />}
                  <button className={`btn ${a.following ? 'border-accent text-ink' : ''}`}
                          onClick={() => relate('follow', !!a.following)}>
                    {a.following ? 'Following' : 'Follow'}
                  </button>
                </>
              ) : (
                <Link to="/auth" className="btn-go">Sign in to subscribe</Link>
              )}
            </div>

            <p className="mt-4 text-sm text-ink-2">{a.sport} · {a.country}</p>
            {a.bio && <p className="mt-2 max-w-2xl text-sm text-ink-2">{a.bio}</p>}

            {/* ── the audience, in one strip ──────────────────────────── */}
            <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
              <Stat n={feedCount} label="post" />
              <Stat n={mediaCount} label="media" plural="media" />
              <Stat n={a.followers ?? 0} label="follower" />
              <Stat n={a.subscribers ?? 0} label="subscriber" />
              {a.socials.length > 0 && (
                <span className="ml-auto flex flex-wrap items-center gap-2">
                  {a.socials.map((s) => (
                    <a key={s.platform} href={s.url} target="_blank" rel="noreferrer noopener"
                       className="tag hover:text-accent">{s.platform}</a>
                  ))}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* ── the work ──────────────────────────────────────────────────── */}
        <div className="mt-5">
          <Tabs
            active={tab}
            onChange={setTab}
            tabs={[
              { key: 'posts', label: 'Posts', count: feedCount },
              { key: 'shop', label: 'Shop', count: shop.length },
              { key: 'memberships', label: 'Memberships' },
              { key: 'wall', label: 'Fan wall', count: wall.length },
            ]}
          />
        </div>

        {error && (
          <div className="mt-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
            {error}
          </div>
        )}

        {tab === 'posts' && (
          <>
            <div className="mt-4 flex flex-wrap gap-2">
              {(['all', 'free', 'unlocked', 'locked'] as const).map((f) => (
                <button key={f} onClick={() => setFilter(f)}
                        className={`rounded-full border px-4 py-1.5 font-display text-[12px]
                                    uppercase tracking-micro transition-colors ${
                          filter === f
                            ? 'border-accent bg-accent text-accent-on'
                            : 'border-line text-ink-3 hover:text-ink-2'}`}>
                  {f === 'all' ? 'All' : f === 'free' ? 'Free'
                    : f === 'unlocked' ? 'Unlocked' : 'Locked'}
                </button>
              ))}
            </div>
            <div className="mt-4">
              {/* Social posts are free content by definition — they are public
                  on the platform they came from — so the Free filter shows them
                  and the paid filters do not. This passed them only under
                  'all', which meant clicking Free *removed* the largest block
                  of free content on the page. */}
              <Wall items={shown} news={filter === 'all' || filter === 'free' ? news : []}
                    onVote={vote}
                    onUnlock={canRelate && !a.subscribed
                      ? () => void relate('subscribe', false)
                      : undefined}
                    empty={filter === 'locked'
                      ? 'Nothing behind the paywall yet.'
                      : 'Nothing on the wall yet.'} />
            </div>
          </>
        )}

        {tab === 'shop' && (
          <div className="mt-4">
            <Shop items={items} empty="Nothing to book yet." />
          </div>
        )}

        {tab === 'wall' && (
          <div className="mt-4">
            <FanWall
              posts={wall}
              canPost={canRelate && (!!a.following || !!a.subscribed)}
              following={!!a.following}
              draft={draft}
              onDraft={setDraft}
              onPost={async () => {
                try {
                  await api.post(`/api/athletes/${slug}/wall-posts`, { body: draft.trim() })
                  setDraft('')
                  setWall(await api.get<FanPost[]>(`/api/athletes/${slug}/wall-posts`))
                } catch (e) { setError(errorText(e)) }
              }}
              onRemove={async (id) => {
                try {
                  await api.del(`/api/wall-posts/${id}`)
                  setWall((list) => list.filter((p) => p.id !== id))
                } catch (e) { setError(errorText(e)) }
              }}
            />
          </div>
        )}

        {tab === 'memberships' && (
          <div className="mt-4">
            <MembershipCard athlete={a} canRelate={canRelate}
                            onJoin={() => relate('subscribe', !!a.subscribed)} />
          </div>
        )}

        {/* Sponsor-facing evidence. Absent from a fan's payload entirely, so
            these do not render rather than rendering empty. */}
        {a.score !== undefined && (
          <Section title="Marketability">
            <DimensionGrid score={a.score} />
          </Section>
        )}
        {a.audience && Object.keys(a.audience).length > 0 && (
          <Section title="Audience">
            <AudiencePanel audience={a.audience} />
          </Section>
        )}
        {a.base_rate_eur !== undefined && (
          <Section title="Commercial">
            <div className="flex flex-wrap gap-2">
              <span className="tag">Rate card {fmtMoney(a.base_rate_eur)}</span>
              {a.deal_types.map((t) => <span key={t} className="tag">{dealTypeLabel(t)}</span>)}
            </div>
          </Section>
        )}
      </div>

      {/* ── the offer, kept in view ─────────────────────────────────────── */}
      <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
        <MembershipCard athlete={a} canRelate={canRelate}
                        onJoin={() => relate('subscribe', !!a.subscribed)} />

        {(a.clubs ?? []).length > 0 && (
          <div className="panel p-4">
            <p className="cap mb-2">Clubs</p>
            {(a.clubs ?? []).map((c) => (
              <Link key={c.slug} to={`/clubs/${c.slug}`}
                    className="block text-sm text-ink hover:text-accent">
                {c.name} <span className="meta">{c.position}</span>
              </Link>
            ))}
          </div>
        )}

        {a.career_highlights.length > 0 && (
          <div className="panel p-4">
            <p className="cap mb-2">Career highlights</p>
            <ul className="space-y-1 text-sm text-ink-2">
              {a.career_highlights.map((h) => (
                <li key={h} className="flex gap-2"><span className="text-accent">—</span>{h}</li>
              ))}
            </ul>
          </div>
        )}
      </aside>
    </div>
  )
}

function Stat({ n, label, plural }: { n: number; label: string; plural?: string }) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="tnum font-display text-[17px] font-bold text-ink">{fmtNum(n)}</span>
      <span className="meta">{n === 1 ? label : plural ?? `${label}s`}</span>
    </span>
  )
}

function MembershipCard({ athlete, canRelate, onJoin }: {
  athlete: Athlete
  canRelate: boolean
  onJoin: () => void
}) {
  const joined = !!athlete.subscribed
  return (
    <div className="panel overflow-hidden">
      <Cover name={athlete.display_name} height="h-20" />
      <div className="p-4">
        <p className="cap text-ink-3">Membership</p>
        <p className="mt-1 font-medium text-ink">{MEMBERSHIP.name}</p>
        <p className="mt-1">
          <span className="font-display text-[26px] font-bold text-ink">{MEMBERSHIP.price}</span>
          <span className="meta">/month</span>
        </p>
        {canRelate ? (
          <button className={joined ? 'btn mt-3 w-full' : 'btn-go mt-3 w-full'} onClick={onJoin}>
            {joined ? 'Leave membership' : 'Join'}
          </button>
        ) : (
          <Link to="/auth" className="btn-go mt-3 block w-full text-center">Sign in to join</Link>
        )}
        <p className="meta mt-2">Free while this is a demo — no card is taken.</p>

        <p className="cap mt-4 mb-1.5">Included</p>
        <ul className="space-y-1 text-xs text-ink-2">
          {MEMBERSHIP.perks.map((perk) => (
            <li key={perk} className="flex gap-2"><span className="text-accent">—</span>{perk}</li>
          ))}
        </ul>
      </div>
    </div>
  )
}


interface FanPost {
  id: number
  body: string
  at: string
  author: string
  role: string
  can_remove: boolean
}

/** What other people say, on somebody else's page.
 *
 *  Posting needs a follow. That is a low bar on purpose — charging for the
 *  right to say "good race" would be a strange thing to sell — but it is a
 *  deliberate act, and an open write surface on the page of somebody with an
 *  audience is a spam target.
 *
 *  `can_remove` comes from the server, so the control never appears where the
 *  delete would be refused.
 */
function FanWall({ posts, canPost, following, draft, onDraft, onPost, onRemove }: {
  posts: FanPost[]
  canPost: boolean
  following: boolean
  draft: string
  onDraft: (v: string) => void
  onPost: () => void
  onRemove: (id: number) => void
}) {
  return (
    <div className="space-y-4">
      {canPost ? (
        <div className="panel p-4">
          <textarea className="field min-h-[4.5rem]" value={draft} maxLength={500}
                    placeholder="Say something" onChange={(e) => onDraft(e.target.value)} />
          <div className="mt-2 flex items-center gap-3">
            <button className="btn-go" disabled={!draft.trim()} onClick={onPost}>Post</button>
            <span className="meta">Everyone can read this. They can remove it.</span>
          </div>
        </div>
      ) : (
        <EmptyNote text={following
          ? 'Sign in to post here.'
          : 'Follow them to post on their wall.'} />
      )}

      {posts.length === 0 ? (
        <EmptyNote text="Nothing on the fan wall yet." />
      ) : (
        <div className="space-y-2">
          {posts.map((p) => (
            <div key={p.id} className="panel flex items-start gap-3 p-4">
              <Avatar name={p.author} size={32} />
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="text-sm font-medium text-ink">{p.author}</span>
                  <span className="cap text-ink-3">{p.role}</span>
                  <span className="meta ml-auto">
                    {new Date(p.at).toLocaleDateString(undefined,
                      { day: 'numeric', month: 'short' })}
                  </span>
                </div>
                <p className="mt-1 whitespace-pre-line text-sm text-ink-2">{p.body}</p>
              </div>
              {p.can_remove && (
                <button className="btn px-2 py-1 text-xs" onClick={() => onRemove(p.id)}>
                  Remove
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
