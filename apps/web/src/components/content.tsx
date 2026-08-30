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
import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import type { ContentItem, NewsItem } from '../types'
import { EmptyNote, Tabs } from './ui'

/** A session or an event is scarce -- it costs the author a day -- so when it
 *  happens, where, and how many places are left are part of the offer. */
function occasion(item: ContentItem): string {
  const at = new Date(item.starts_at as string)
  const stamp = at.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
    + ', ' + at.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  return [stamp, item.location || 'Location to be confirmed',
          item.capacity ? `${item.capacity} places` : null].filter(Boolean).join(' · ')
}

export function ContentCard({ item, showAuthor = false }: {
  item: ContentItem
  showAuthor?: boolean
}) {
  return (
    <article className="panel p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="cap text-ink-3">{item.kind}</span>
        <h3 className="font-medium text-ink">{item.title}</h3>
        {item.label === 'sponsored' && (
          <span className="tag border-warn text-warn">Sponsored · {item.sponsor_name}</span>
        )}
        {item.label === 'highlighted' && <span className="tag text-accent-ink">Highlighted</span>}
        {/* "Free" means "not locked", which is true of a product and also
            entirely the wrong word for a signed cap that costs money on the
            store. A product carries no tier tag at all; its price lives where
            it is actually sold. */}
        {item.kind !== 'product' && (
          <span className={`ml-auto tag ${item.locked ? '' : 'text-ok'}`}>
            {item.locked ? item.tier_label : 'Free'}
          </span>
        )}
      </div>

      {showAuthor && item.author && item.author_slug && (
        <Link to={`/athletes/${item.author_slug}`} className="meta mt-1 block hover:text-accent">
          {item.author}
        </Link>
      )}

      {item.starts_at && <p className="meta mt-1">{occasion(item)}</p>}

      {item.kind === 'product' && item.external_url && (
        <p className="mt-2">
          <a href={item.external_url} target="_blank" rel="noreferrer noopener"
             className="meta hover:text-accent">
            Buy on {storeName(item.external_url)} &rarr;
          </a>
        </p>
      )}

      {item.locked ? (
        <p className="mt-3 rounded border border-line bg-raised px-3 py-2 text-sm text-ink-3">
          Locked — {item.tier_label} opens it.{' '}
          <span className="meta">Fan subscriptions are not live in this demo.</span>
        </p>
      ) : (
        item.body && <p className="mt-3 whitespace-pre-line text-sm text-ink-2">{item.body}</p>
      )}
    </article>
  )
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

function stamp(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined,
    { day: 'numeric', month: 'short', year: 'numeric' })
}

/** Something the athlete posted on their own platform. It is not for sale and
 *  never locked -- it is already public, and it is what keeps a wall worth
 *  opening on a week the athlete has published nothing here. */
function NewsCard({ item }: { item: NewsItem }) {
  return (
    <article className="panel p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="cap text-ink-3">{item.platform}</span>
        <h3 className="min-w-0 font-medium text-ink-2">{item.title}</h3>
        <a href={item.permalink} target="_blank" rel="noreferrer noopener"
           className="ml-auto meta hover:text-accent">Open on {item.platform} &rarr;</a>
      </div>
      <p className="meta mt-1">{stamp(item.published_at)}</p>
    </article>
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
  const own = items.filter((i) => i.kind !== 'post' || i.part_of == null)
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
export function Wall({ items, news = [], showAuthor = false, empty }: {
  items: ContentItem[]
  news?: NewsItem[]
  showAuthor?: boolean
  empty: string
}) {
  const posts = items.filter((i) => i.kind === 'post' && i.part_of == null)

  const entries: { key: string; at: number; node: ReactNode }[] = [
    ...posts.map((i) => ({
      key: `c${i.id}`,
      at: new Date(i.published_at ?? 0).getTime(),
      node: <ContentCard item={i} showAuthor={showAuthor} />,
    })),
    ...news.map((n, idx) => ({
      key: `n${idx}-${n.permalink}`,
      at: new Date(n.published_at).getTime(),
      node: <NewsCard item={n} />,
    })),
  ].sort((a, b) => b.at - a.at)

  if (entries.length === 0) return <EmptyNote text={empty} />
  return <div className="space-y-2">{entries.map((e) => <div key={e.key}>{e.node}</div>)}</div>
}

/** The public pair, so an athlete profile and a club page cannot drift on
 *  either the split or the words for it. */
export function ContentTabs({ items, news = [] }: {
  items: ContentItem[]
  news?: NewsItem[]
}) {
  const posts = items.filter((i) => i.kind === 'post' && i.part_of == null)
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
          ? <Wall items={items} news={news}
                  empty="Nothing on the wall yet." />
          : <Shop items={items} empty="Nothing to book yet." />}
      </div>
    </div>
  )
}
