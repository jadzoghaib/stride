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

type Tab = 'posts' | 'shop' | 'memberships'
type Filter = 'all' | 'free' | 'locked'

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
  const [filter, setFilter] = useState<Filter>('all')
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Athlete>(`/api/athletes/${slug}`).then(setA).catch((e) => setError(errorText(e)))
    api.get<ContentItem[]>(`/api/athletes/${slug}/content`).then(setContent).catch(() => setContent([]))
    api.get<NewsItem[]>(`/api/athletes/${slug}/news`).then(setNews).catch(() => setNews([]))
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
    if (filter === 'free') return items.filter((i) => !i.locked)
    if (filter === 'locked') return items.filter((i) => i.locked)
    return items
  }, [items, filter])
  const mediaCount = items.filter((i) => i.has_media || i.media_url).length

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
              <Stat n={posts.length} label="post" />
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
              { key: 'posts', label: 'Posts', count: posts.length + news.length },
              { key: 'shop', label: 'Shop', count: shop.length },
              { key: 'memberships', label: 'Memberships' },
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
              {(['all', 'free', 'locked'] as const).map((f) => (
                <button key={f} onClick={() => setFilter(f)}
                        className={`rounded-full border px-4 py-1.5 font-display text-[12px]
                                    uppercase tracking-micro transition-colors ${
                          filter === f
                            ? 'border-accent bg-accent text-accent-on'
                            : 'border-line text-ink-3 hover:text-ink-2'}`}>
                  {f === 'all' ? 'All' : f === 'free' ? 'Free' : 'Subscribers'}
                </button>
              ))}
            </div>
            <div className="mt-4">
              <Wall items={shown} news={filter === 'all' ? news : []} onVote={vote}
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
