/** The reader's half of the content model, split the way a fan meets it.
 *
 *  Two surfaces, not one list:
 *
 *    Wall   posts, newest first, some free and some locked, mixed in with
 *           what this person posts on their own platforms. You do not buy a
 *           wall, you follow it.
 *    Shop   courses, sessions and events -- the things a fan decides on, pays
 *           for once, and receives. A price and a date are the point here
 *           rather than an interruption.
 *
 *  The first cut of this split on scarcity instead, which put "come train with
 *  me" on the wall: the highest-value thing on the page, buried in a stream and
 *  scrolling away. What a fan *does* is the line that matters.
 *
 *  A locked item withholds the body and only the body. Kind, title, schedule,
 *  sponsor disclosure and the tier it would take all stay visible, because
 *  nobody can judge whether something is worth paying for without seeing its
 *  shape. There is deliberately no checkout: no payments stack exists yet, and
 *  a button that took money nowhere would be the one dishonest control here.
 */
import { Lock } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { ContentItem, NewsItem } from '../types'
import { Avatar, EmptyNote, Tabs } from './ui'

/** A session or an event is scarce -- it costs the author a day -- so when it
 *  happens, where, and how many places are left are part of the offer. */
function occasion(item: ContentItem): string {
  const at = new Date(item.starts_at as string)
  const stamp = at.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    + ', ' + at.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  return [stamp, item.location || 'Location to be confirmed',
          item.capacity ? `${item.capacity} places` : null].filter(Boolean).join(' · ')
}

function stamp(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined,
    { day: 'numeric', month: 'short', year: 'numeric' })
}

/** The domain a product link points at, so a fan knows where they are going
 *  before they click. Stride does not sell merch -- it says who does. */
function storeName(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return 'their store'
  }
}

/** Something the athlete posted on their own platform. Never locked -- it is
 *  already public, and it is what keeps a wall worth opening in a week the
 *  athlete has published nothing here. */
/** A wash per platform, so a synced post is distinguishable from one written
 *  here at a glance.
 *
 *  Kept to about 6% because the point is to separate two *kinds* of card, not
 *  to decorate: at full strength three brand colours would fight the amber the
 *  rest of the product is built on and turn a feed into a paint chart. The
 *  alpha also means one definition works on both themes — the tint composites
 *  over whatever panel colour is behind it rather than replacing it.
 *
 *  Colour is never the only signal. Every card already names its platform in
 *  the label and in "Open on ...", which is what keeps this readable for anyone
 *  who cannot separate the three hues.
 */
const PLATFORM_TINT: Record<string, { wash: string; edge: string; ink: string }> = {
  // The purple end of Instagram's gradient rather than the pink. At 6% the pink
  // composited to rgb(251,243,248) and YouTube's red to rgb(255,242,245) — two
  // pale pinks a reader cannot tell apart, which defeats the point of colouring
  // them at all. Purple, cyan and red separate cleanly at this strength.
  // The washes stay as raw brand rgba: at 5-7% alpha they are texture, not
  // text, and contrast does not apply. The inks are label text, so they come
  // from the token layer, re-weighted per theme to clear 4.5:1 on `panel`.
  instagram: { wash: 'rgba(131, 58, 180, 0.07)', edge: 'rgba(131, 58, 180, 0.32)', ink: 'rgb(var(--c-plat-instagram))' },
  tiktok:    { wash: 'rgba(0, 194, 203, 0.07)',  edge: 'rgba(0, 194, 203, 0.34)',  ink: 'rgb(var(--c-plat-tiktok))' },
  youtube:   { wash: 'rgba(255, 0, 51, 0.05)',   edge: 'rgba(255, 0, 51, 0.26)',   ink: 'rgb(var(--c-plat-youtube))' },
}

function NewsCard({ item, showAuthor = false }: { item: NewsItem; showAuthor?: boolean }) {
  const tint = PLATFORM_TINT[item.platform.toLowerCase()]
  return (
    <article className="panel p-4" style={tint ? {
      backgroundColor: tint.wash,
      borderColor: tint.edge,
      // A slightly stronger edge on one side: the wash alone is deliberately
      // faint, and this makes the two kinds of card separable while scrolling
      // without making the tint heavier.
      borderLeftWidth: 3,
      borderLeftColor: tint.ink,
    } : undefined}>
      {/* In a follower feed these are mixed in among several athletes, so the
          card has to say whose it is. On an athlete's own page the whole page
          already answers that, and repeating it on every row is noise. */}
      {showAuthor && item.author && (
        <div className="mb-2 flex items-center gap-2.5">
          <Avatar name={item.author} size={28} />
          {item.author_slug ? (
            <Link to={`/athletes/${item.author_slug}`}
                  className="text-sm font-medium text-ink hover:text-accent">
              {item.author}
            </Link>
          ) : (
            <span className="text-sm font-medium text-ink">{item.author}</span>
          )}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className="cap" style={tint ? { color: tint.ink } : undefined}>{item.platform}</span>
        <h3 className="min-w-0 font-medium text-ink-2">{item.title}</h3>
        <a href={item.permalink} target="_blank" rel="noreferrer noopener"
           className="ml-auto meta hover:text-accent">Open on {item.platform} &rarr;</a>
      </div>
      <p className="meta mt-1">{stamp(item.published_at)}</p>
    </article>
  )
}


/** What a locked post looks like.
 *
 *  Modelled on the reference product, with one deliberate difference: there is
 *  no blurred thumbnail under the lock, because the server does not send one.
 *  A blur is a client-side filter over bytes the reader already has -- it looks
 *  like a wall and is a curtain, removable with the element inspector. Locked
 *  items arrive with `media_url` withheld entirely and only a `has_media` flag,
 *  so the panel below is drawn rather than obscured.
 *
 *  It still has to read as *a picture you do not have yet* rather than as an
 *  error, which is what the old 44px grey strip read as. Hence the real media
 *  aspect, the athlete's own cover palette, and the count line underneath: the
 *  shape of the thing is the honest part of it.
 */
function LockedPanel({ item, onUnlock }: {
  item: ContentItem
  onUnlock?: () => void
}) {
  const noun = item.media_kind === 'video' ? 'video'
    : item.media_kind === 'image' ? 'image'
    : item.kind === 'poll' ? 'poll' : 'post'

  const cta = (
    <span className="inline-flex items-center gap-2 rounded-full bg-panel/95 px-4 py-2
                     font-display text-small uppercase tracking-micro text-ink shadow-sm
                     ring-1 ring-line transition-transform group-hover:scale-[1.03]">
      <Lock size={13} strokeWidth={2.2} />
      Subscribe to unlock
    </span>
  )

  return (
    <div className="relative mt-3 border-y border-line">
      {/* The field. Every layer is a background paint and none of them is a
          filter -- a radial gradient gives the corner glow that `blur-2xl` on a
          circle would, without putting a filtered layer in the compositor for
          every locked card on the page. */}
      <div className="relative flex h-64 items-center justify-center overflow-hidden" style={{
        backgroundImage: [
          'radial-gradient(38rem 18rem at 88% 0%, rgba(255,176,32,0.22), transparent 60%)',
          'repeating-linear-gradient(45deg, rgba(255,255,255,0.045) 0 2px, transparent 2px 22px)',
          'linear-gradient(135deg, #1d3b2a 0%, #16281f 55%, #0f1a14 100%)',
        ].join(', '),
      }}>
        <div className="relative flex flex-col items-center gap-3">
          {/* Three routes to the same intent, and never a dead control: the
              subscribe action where the viewer can take it, the athlete's page
              where the lock is met in a feed, and the sign-in page otherwise.
              A signed-out reader used to get a chip that read "Subscribe to
              unlock" and did nothing at all when clicked. */}
          {onUnlock ? (
            <button onClick={onUnlock} className="group" aria-label="Subscribe to unlock this post">
              {cta}
            </button>
          ) : (
            <Link className="group"
                  to={item.author_slug ? `/athletes/${item.author_slug}` : '/auth'}>
              {cta}
            </Link>
          )}
          <span className="font-mono text-fine text-white/70">
            1 {noun} · subscribers only
          </span>
        </div>
      </div>
    </div>
  )
}

export function ContentCard({ item, showAuthor = false, onVote, onUnlock }: {
  item: ContentItem
  showAuthor?: boolean
  onVote?: (item: ContentItem, optionId: number) => void
  onUnlock?: () => void
}) {
  const paid = item.locked

  return (
    <article className="panel overflow-hidden">
      {/* Author first, then the media, then the words. A feed is read by
          skimming faces and pictures; putting a kind label above both was a
          filing system, not a post. */}
      {showAuthor && item.author && item.author_slug ? (
        <Link to={`/athletes/${item.author_slug}`}
              className="flex items-center gap-2.5 px-4 pt-4 hover:text-accent">
          <Avatar name={item.author} size={34} />
          <div className="min-w-0">
            <div className="text-sm font-medium text-ink">{item.author}</div>
            <div className="meta">{item.published_at ? stamp(item.published_at) : 'draft'}</div>
          </div>
          <Badges item={item} />
        </Link>
      ) : (
        <div className="flex items-center gap-2 px-4 pt-4">
          <span className="cap text-ink-3">{item.kind}</span>
          <Badges item={item} />
        </div>
      )}

      {/* the picture, or the shape of the one being withheld */}
      {!paid && item.media_url && item.media_kind === 'image' && (
        // A link can rot, and a broken-image icon in the middle of a post is
        // worse than a post with no picture. Hide it and keep the words.
        <img src={item.media_url} alt="" loading="lazy"
             onError={(e) => { e.currentTarget.style.display = 'none' }}
             className="mt-3 max-h-[26rem] w-full object-cover" />
      )}
      {!paid && item.media_url && item.media_kind === 'video' && (
        <video src={item.media_url} controls preload="metadata"
               className="mt-3 max-h-[26rem] w-full bg-ground object-cover" />
      )}
      {paid && <LockedPanel item={item} onUnlock={onUnlock} />}

      <div className="p-4">
        <h3 className="font-medium text-ink">{item.title}</h3>

        {item.starts_at && <p className="meta mt-1">{occasion(item)}</p>}

        {item.kind === 'product' && item.external_url && (
          <p className="mt-2">
            <a href={item.external_url} target="_blank" rel="noreferrer noopener"
               className="meta hover:text-accent">
              Buy on {storeName(item.external_url)} &rarr;
            </a>
          </p>
        )}

        {paid ? (
          <p className="meta mt-2">Subscriptions are free while this is a demo.</p>
        ) : (
          <>
            {item.body && (
              <p className="mt-2 whitespace-pre-line text-sm text-ink-2">{item.body}</p>
            )}
            {item.poll && <Poll item={item} onVote={onVote} />}
          </>
        )}
      </div>
    </article>
  )
}

function Badges({ item }: { item: ContentItem }) {
  return (
    <span className="ml-auto flex shrink-0 items-center gap-2">
      {item.label === 'sponsored' && (
        <span className="tag tag-warn">Sponsored · {item.sponsor_name}</span>
      )}
      {item.label === 'highlighted' && <span className="tag text-accent-ink">Highlighted</span>}
      {item.kind !== 'product' && (
        <span className={`tag ${item.locked ? '' : 'text-ok'}`}>
          {item.locked ? item.tier_label : 'Everyone'}
        </span>
      )}
    </span>
  )
}

/** Results are always visible, including before voting. A poll that hides its
 *  answer until you commit is a different product and a worse one: the reason
 *  to ask an audience is to show them what the audience said. */
function Poll({ item, onVote }: {
  item: ContentItem
  onVote?: (item: ContentItem, optionId: number) => void
}) {
  const poll = item.poll
  if (!poll) return null
  return (
    <div className="mt-3 space-y-1.5">
      {poll.options.map((o) => {
        const mine = poll.voted === o.id
        return (
          <button key={o.id} disabled={!onVote}
                  onClick={() => onVote?.(item, o.id)}
                  className={`relative block w-full overflow-hidden rounded border px-3 py-2
                              text-left text-sm ${mine ? 'border-accent text-ink' : 'border-line text-ink-2'}
                              ${onVote ? 'hover:border-accent/60' : 'cursor-default'}`}>
            <span className="absolute inset-y-0 left-0 bg-accent/15" style={{ width: `${o.share}%` }} />
            <span className="relative flex items-center gap-2">
              {o.label}
              <span className="tnum ml-auto text-xs text-ink-3">{o.share}%</span>
            </span>
          </button>
        )
      })}
      <p className="meta">{poll.total} vote{poll.total === 1 ? '' : 's'}</p>
    </div>
  )
}

/** The shop: what a fan can buy or book -- courses, sessions, events.

 *  Named for the category rather than for anything in it. An early version
 *  called this "Train with me", which was the title of one event inside it and
 *  would have had to be renamed the day an athlete sold a race analysis or a
 *  1:1 call. "Shop" is also the same word for an athlete and a club, so the two
 *  pages stop needing different pronouns for the same idea.
 *
 *  The line here is what the fan *does*, not what it costs the athlete to make.
 *  A course and a "come train with me" morning feel unrelated -- one is a file,
 *  one is a Saturday -- but a fan meets them the same way: decide, pay once,
 *  receive a specific thing. A post is the opposite: you do not buy it, you
 *  subscribe and it arrives. Splitting on scarcity instead put the session on
 *  the wall, which buried the highest-value thing on the page in a stream.
 *
 *  Dated things come first and soonest-first, because they expire. Past ones
 *  stay, muted: nobody can attend last month's session, but "they have run nine
 *  of these" is the strongest argument for booking the tenth.
 */
export function Shop({ items, empty }: { items: ContentItem[]; empty: string }) {
  const now = Date.now()
  const own = items.filter((i) => (i.kind !== 'post' && i.kind !== 'poll') || i.part_of == null)
  const courses = own.filter((i) => i.kind === 'course')
  const products = own.filter((i) => i.kind === 'product')
  const dated = own.filter((i) => i.starts_at)
  const upcoming = dated
    .filter((i) => new Date(i.starts_at as string).getTime() > now)
    .sort((a, b) => +new Date(a.starts_at as string) - +new Date(b.starts_at as string))
  const past = dated
    .filter((i) => new Date(i.starts_at as string).getTime() <= now)
    .sort((a, b) => +new Date(b.starts_at as string) - +new Date(a.starts_at as string))
  const partsOf = (id: number) =>
    items.filter((i) => i.part_of === id).sort((a, b) => (a.position ?? 0) - (b.position ?? 0))

  if (courses.length === 0 && dated.length === 0 && products.length === 0) {
    return <EmptyNote text={empty} />
  }

  return (
    <div className="space-y-6">
      {upcoming.length > 0 && (
        <div>
          <p className="cap mb-2 text-accent-ink">Coming up</p>
          <div className="space-y-2">
            {upcoming.map((i) => <ContentCard key={i.id} item={i} />)}
          </div>
        </div>
      )}

      {courses.length > 0 && (
        <div>
          {(upcoming.length > 0 || past.length > 0) && <p className="cap mb-2">Courses</p>}
          <div className="space-y-3">
            {courses.map((c) => (
              <div key={c.id}>
                <ContentCard item={c} />
                {partsOf(c.id).length > 0 && (
                  <div className="mt-2 space-y-2 border-l border-line pl-4">
                    {partsOf(c.id).map((part) => <ContentCard key={part.id} item={part} />)}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {products.length > 0 && (
        <div>
          <p className="cap mb-2">Merch</p>
          <div className="space-y-2">
            {products.map((i) => <ContentCard key={i.id} item={i} />)}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <div className="opacity-60">
          <p className="cap mb-2 text-ink-3">Already happened</p>
          <div className="space-y-2">
            {past.map((i) => <ContentCard key={i.id} item={i} />)}
          </div>
        </div>
      )}
    </div>
  )
}

/** The wall: posts, newest first, some free and some not.
 *
 *  Two streams in one, because a fan does not care which system produced a row
 *  -- what this person wrote here, and what they posted on their own platforms.
 *  Nothing bookable appears; that has a tab of its own, where a price and a
 *  date are the point rather than an interruption.
 */
export function Wall({ items, news = [], showAuthor = false, empty, onVote, onUnlock }: {
  items: ContentItem[]
  news?: NewsItem[]
  showAuthor?: boolean
  empty: string
  onVote?: (item: ContentItem, optionId: number) => void
  onUnlock?: () => void
}) {
  const posts = items.filter((i) => (i.kind === 'post' || i.kind === 'poll') && i.part_of == null)

  const entries: { key: string; at: number; node: ReactNode }[] = [
    ...posts.map((i) => ({
      key: `c${i.id}`,
      at: new Date(i.published_at ?? 0).getTime(),
      node: <ContentCard item={i} showAuthor={showAuthor} onVote={onVote} onUnlock={onUnlock} />,
    })),
    ...news.map((n, idx) => ({
      key: `n${idx}-${n.permalink}`,
      at: new Date(n.published_at).getTime(),
      node: <NewsCard item={n} showAuthor={showAuthor} />,
    })),
  ].sort((a, b) => b.at - a.at)

  if (entries.length === 0) return <EmptyNote text={empty} />
  return <div className="space-y-2">{entries.map((e) => <div key={e.key}>{e.node}</div>)}</div>
}

/** The public pair, so an athlete profile and a club page cannot drift on
 *  either the split or the words for it. */
export function ContentTabs({ items, news = [], onVote }: {
  items: ContentItem[]
  news?: NewsItem[]
  onVote?: (item: ContentItem, optionId: number) => void
}) {
  const posts = items.filter((i) => (i.kind === 'post' || i.kind === 'poll') && i.part_of == null)
  const offerings = items.filter((i) => i.kind === 'course' || i.kind === 'product'
    || (i.starts_at != null && i.kind !== 'post'))
  // Open on the wall, except when there is no wall to open on. A club that
  // runs one open session and posts nothing would otherwise greet every
  // visitor with an empty panel and its only product one click away.
  const [tab, setTab] = useState<'wall' | 'shop'>(
    posts.length + news.length === 0 && offerings.length > 0 ? 'shop' : 'wall')

  return (
    <div>
      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: 'wall', label: 'Wall', count: posts.length + news.length },
          { key: 'shop', label: 'Shop', count: offerings.length },
        ]}
      />
      <div className="mt-4">
        {tab === 'wall'
          ? <Wall items={items} news={news} onVote={onVote}
                  empty="Nothing on the wall yet." />
          : <Shop items={items} empty="Nothing to book yet." />}
      </div>
    </div>
  )
}
