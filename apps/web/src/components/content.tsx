/** The reader's half of the content model.
 *
 *  `/api/athletes/{slug}/content`, `/api/clubs/{slug}/content` and
 *  `/api/feed/content` all shipped with tests, and none of them had a caller.
 *  An athlete could write a course, publish it, and no screen in the product
 *  would ever show it to anybody: the server was right and the app was empty.
 *  This is the missing half, shared by the athlete profile, the club profile
 *  and the feed so those three cannot drift on what a lock is allowed to hide.
 *
 *  A locked item withholds the body and only the body. Kind, title, schedule,
 *  sponsor disclosure and the tier it would take all stay visible, because
 *  nobody can judge whether something is worth paying for without seeing its
 *  shape. There is deliberately no checkout: no payments stack exists yet, and
 *  a button that took money nowhere would be the one dishonest control here.
 */
import { Link } from 'react-router-dom'
import type { ContentItem } from '../types'
import { EmptyNote } from './ui'

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
        <span className={`ml-auto tag ${item.locked ? '' : 'text-ok'}`}>
          {item.locked ? item.tier_label : 'Free'}
        </span>
      </div>

      {showAuthor && item.author && item.author_slug && (
        <Link to={`/athletes/${item.author_slug}`} className="meta mt-1 block hover:text-accent">
          {item.author}
        </Link>
      )}

      {item.starts_at && <p className="meta mt-1">{occasion(item)}</p>}

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

export function ContentList({ items, showAuthor = false, empty }: {
  items: ContentItem[]
  showAuthor?: boolean
  empty: string
}) {
  if (items.length === 0) return <EmptyNote text={empty} />

  // A course is a series; its parts belong under it rather than loose in the
  // list, in the order the author gave them.
  const courses = items.filter((i) => i.kind === 'course')
  const partsOf = (id: number) =>
    items.filter((i) => i.part_of === id).sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
  const loose = items.filter((i) => i.kind !== 'course' && !i.part_of)

  return (
    <div className="space-y-3">
      {courses.map((c) => (
        <div key={c.id}>
          <ContentCard item={c} showAuthor={showAuthor} />
          {partsOf(c.id).length > 0 && (
            <div className="mt-2 space-y-2 border-l border-line pl-4">
              {partsOf(c.id).map((p) => <ContentCard key={p.id} item={p} showAuthor={false} />)}
            </div>
          )}
        </div>
      ))}
      {loose.map((i) => <ContentCard key={i.id} item={i} showAuthor={showAuthor} />)}
    </div>
  )
}
