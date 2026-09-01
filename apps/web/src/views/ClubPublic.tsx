import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ContentTabs } from '../components/content'
import { LoadError, PageHeader, PageLoading, Avatar, EmptyNote, Section } from '../components/ui'
import { api, errorText } from '../lib/api'
import { useAuth } from '../lib/auth'
import { fmtMoney } from '../lib/format'
import type { Club, ClubPackage, ContentItem, RosterMember } from '../types'

interface ClubDetail extends Club {
  roster: RosterMember[]
  packages: ClubPackage[]
}

export default function ClubPublic() {
  const { slug } = useParams()
  const { me } = useAuth()
  const [club, setClub] = useState<ClubDetail | null>(null)
  const [content, setContent] = useState<ContentItem[] | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const load = () =>
    api.get<ClubDetail>(`/api/clubs/${slug}`).then(setClub).catch((e) => setError(errorText(e)))
  useEffect(() => {
    void load()
    // Separate failure: a club with no published sessions is ordinary, and a
    // content error must not take the packages and the roster down with it.
    api.get<ContentItem[]>(`/api/clubs/${slug}/content`).then(setContent).catch(() => setContent([]))
  }, [slug])

  /** Club-wide packages first, then one block per athlete. Sorted by name so
   *  the order does not shuffle between loads. */
  const clubWide = (club?.packages ?? []).filter((p) => !p.athlete_slug)
  const byAthlete = Object.entries(
    (club?.packages ?? []).filter((p) => p.athlete_slug).reduce((acc, p) => {
      const slug = p.athlete_slug as string
      acc[slug] ??= {
        name: p.athlete_name ?? slug,
        position: club?.roster.find((m) => m.slug === slug)?.position ?? '',
        packages: [],
      }
      acc[slug].packages.push(p)
      return acc
    }, {} as Record<string, { name: string; position: string; packages: ClubPackage[] }>),
  ).sort(([, a], [, b]) => a.name.localeCompare(b.name))

  const back = async (p: ClubPackage) => {
    setError('')
    setNotice('')
    try {
      await api.post(`/api/clubs/packages/${p.id}/commit`)
      setNotice(`You are now backing "${p.name}" — track it in your pipeline.`)
      await load()
    } catch (e) {
      setError(errorText(e))
    }
  }

  if (!club) return error ? <LoadError text={error} /> : <PageLoading />

  return (
    <div>
      <PageHeader
        eyebrow="Club"
        title={club.name}
        lede={club.bio}
        tags={
          <>
            <span className="tag">{club.sport}</span>
            <span className="tag">{club.country}</span>
            <span className="tag">{club.region}</span>
          </>
        }
        aside={<span className="meta">{club.backer_count} active backers</span>}
      />
      {notice && <div className="mb-4 rounded border border-ok/45 bg-ok/10 px-3.5 py-2.5 text-sm text-ok">{notice}</div>}
      {error && <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">{error}</div>}

      {/* Grouped by who is being backed, not listed flat.
          A player-direct package is a deal with *that athlete*, sold through
          the club, and a sponsor shopping for one is shopping for a person.
          A flat list buried the name in a chip and made two packages for the
          same athlete look unrelated. */}
      <Section title="Sponsorship packages">
        {club.packages.length === 0 && <EmptyNote text="No active packages." />}

        {clubWide.length > 0 && (
          <>
            <p className="cap mb-2 text-ink-3">The club</p>
            <div className="grid gap-3 md:grid-cols-2">
              {clubWide.map((p) => (
                <PackageCard key={p.id} pkg={p} canBack={me?.role === 'sponsor'} onBack={back} />
              ))}
            </div>
          </>
        )}

        {byAthlete.map(([slug, group]) => (
          <div key={slug} className="mt-6">
            <div className="mb-2 flex items-center gap-2.5">
              <Avatar name={group.name} size={30} />
              <Link to={`/athletes/${slug}`} className="font-medium text-ink hover:text-accent">
                {group.name}
              </Link>
              <span className="meta">
                {group.packages.length} package{group.packages.length === 1 ? '' : 's'}
                {group.position ? ` · ${group.position}` : ''}
              </span>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {group.packages.map((p) => (
                <PackageCard key={p.id} pkg={p} canBack={me?.role === 'sponsor'} onBack={back} />
              ))}
            </div>
          </div>
        ))}
      </Section>

      {content && content.length > 0 && (
        <Section title="From this club">
          <ContentTabs items={content} />
        </Section>
      )}

      <Section title={`Roster (${club.roster.length})`}>
        <div className="grid gap-2 md:grid-cols-2">
          {club.roster.map((m) => (
            <Link key={m.athlete_id} to={`/athletes/${m.slug}`} className="panel panel-hover flex items-center gap-3 p-3">
              <Avatar name={m.display_name} size={36} />
              <div>
                <div className="text-sm font-medium text-ink">{m.display_name}</div>
                <div className="text-xs text-ink-3">{m.position || m.sport} · {m.country}</div>
              </div>
            </Link>
          ))}
        </div>
      </Section>
    </div>
  )
}


function PackageCard({ pkg, canBack, onBack }: {
  pkg: ClubPackage
  canBack: boolean
  onBack: (p: ClubPackage) => void
}) {
  return (
    <div className="panel p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-medium text-ink">{pkg.name}</div>
          <span className={`tag mt-1 inline-block ${
            pkg.package_type === 'player_direct' ? 'border-accent text-ink' : ''}`}>
            {pkg.package_type === 'player_direct' ? 'Player-direct' : 'Club package'}
          </span>
        </div>
        <div className="tnum text-lg font-semibold text-ink">{fmtMoney(pkg.price_eur)}</div>
      </div>
      {pkg.description && <p className="mt-2 text-sm text-ink-2">{pkg.description}</p>}
      {pkg.perks.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-ink-3">
          {pkg.perks.map((perk) => <li key={perk}>· {perk}</li>)}
        </ul>
      )}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-ink-3">
          {pkg.active_backers} active backer{pkg.active_backers === 1 ? '' : 's'}
        </span>
        {canBack && (
          <button className="btn-go px-3 py-1.5 text-xs" onClick={() => onBack(pkg)}>
            Back this package
          </button>
        )}
      </div>
    </div>
  )
}
