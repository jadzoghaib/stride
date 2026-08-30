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

      <Section title="Sponsorship packages">
        {club.packages.length === 0 && <EmptyNote text="No active packages." />}
        <div className="grid gap-3 md:grid-cols-2">
          {club.packages.map((p) => (
            <div key={p.id} className="panel p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="font-medium text-ink">{p.name}</div>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <span className={`tag ${p.package_type === 'player_direct' ? 'border-accent text-ink' : ''}`}>
                      {p.package_type === 'player_direct' ? 'Player-direct' : 'Club package'}
                    </span>
                    {p.athlete_slug && (
                      <Link to={`/athletes/${p.athlete_slug}`} className="tag hover:border-accent">
                        {p.athlete_name}
                      </Link>
                    )}
                  </div>
                </div>
                <div className="tnum text-lg font-semibold text-ink">{fmtMoney(p.price_eur)}</div>
              </div>
              {p.description && <p className="mt-2 text-sm text-ink-2">{p.description}</p>}
              {p.perks.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-xs text-ink-3">
                  {p.perks.map((perk) => <li key={perk}>· {perk}</li>)}
                </ul>
              )}
              <div className="mt-3 flex items-center justify-between">
                <span className="text-xs text-ink-3">{p.active_backers} active backer{p.active_backers === 1 ? '' : 's'}</span>
                {me?.role === 'sponsor' && (
                  <button className="btn-go px-3 py-1.5 text-xs" onClick={() => back(p)}>
                    Back this package
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
        {me?.role !== 'sponsor' && (
          <p className="mt-3 text-xs text-ink-3">Sponsors can back packages from their account.</p>
        )}
      </Section>

      {content && content.length > 0 && (
        <Section title="From this club">
          <ContentTabs items={content} offeringsLabel="Train with us" />
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
