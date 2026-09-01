/** The clubs *you* are in — not the directory of all of them.
 *
 *  This nav slot used to point at the public club directory, which the Directory
 *  item beside it already covered. Two entries, one destination, and neither of
 *  them answered the question an athlete actually opens this page with: *am I
 *  on a roster, and who put me there?*
 *
 *  So it answers that first, and then offers the three things you can do about
 *  it — respond to an invitation, redeem a link a club sent you, or go looking
 *  for one. An athlete belongs to no club by default and that is a normal state,
 *  not an error, so the empty case is written as a starting point rather than as
 *  a warning.
 */
import { Shield } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Avatar, EmptyNote, LoadError, PageHeader, PageLoading, Section } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useToast } from '../../lib/toast'
import type { AthleteWorkspace, ClubInvitation } from '../../types'

export default function MyClubs() {
  const [ws, setWs] = useState<AthleteWorkspace | null>(null)
  const [invites, setInvites] = useState<ClubInvitation[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const toast = useToast()

  const load = async () => {
    try {
      const [workspace, invitations] = await Promise.all([
        api.get<AthleteWorkspace>('/api/athlete/workspace'),
        api.get<ClubInvitation[]>('/api/athlete/invitations').catch(() => []),
      ])
      setWs(workspace)
      setInvites(invitations)
    } catch (e) {
      setError(errorText(e))
    }
  }
  useEffect(() => { void load() }, [])

  const respond = async (invite: ClubInvitation, action: 'accept' | 'decline') => {
    setBusy(invite.invitation_id)
    try {
      await api.post(`/api/athlete/invitations/${invite.invitation_id}/respond`, { action })
      toast(action === 'accept' ? `You are on ${invite.name}'s roster` : `Declined ${invite.name}`)
      await load()
    } catch (e) {
      setError(errorText(e))
    } finally {
      setBusy(null)
    }
  }

  if (!ws) return error ? <LoadError text={error} /> : <PageLoading />

  const clubs = ws.clubs ?? []

  return (
    <div>
      <PageHeader
        eyebrow="Athlete"
        title="My clubs"
        lede="The rosters you are on, and any club waiting on your answer."
        aside={<span className="meta">
          {clubs.length} club{clubs.length === 1 ? '' : 's'}
          {invites.length > 0 ? ` · ${invites.length} invitation${invites.length === 1 ? '' : 's'}` : ''}
        </span>}
      />

      {error && (
        <div className="mb-4 rounded border border-critical/45 bg-critical/10 px-3.5 py-2.5 text-sm text-critical">
          {error}
        </div>
      )}

      {invites.length > 0 && (
        <Section title={`Invitations (${invites.length})`}
                 aside={<span className="meta">a club cannot add you without this</span>}>
          <div className="space-y-2">
            {invites.map((i) => (
              <div key={i.invitation_id} className="panel flex flex-wrap items-center gap-3 p-4">
                <Avatar name={i.name} size={34} />
                <div className="min-w-0">
                  <Link to={`/clubs/${i.slug}`} className="font-medium text-ink hover:text-accent">
                    {i.name}
                  </Link>
                  <div className="text-xs text-ink-3">
                    {i.sport} · {i.country}{i.position ? ` · as ${i.position}` : ''}
                  </div>
                </div>
                <p className="meta max-w-md">
                  Joining lets them build sponsorship packages around you, and vouch for you in
                  admission. You can leave later.
                </p>
                <div className="ml-auto flex gap-2">
                  <button className="btn-go px-3 py-1.5 text-xs" disabled={busy === i.invitation_id}
                          onClick={() => void respond(i, 'accept')}>Accept</button>
                  <button className="btn px-3 py-1.5 text-xs" disabled={busy === i.invitation_id}
                          onClick={() => void respond(i, 'decline')}>Decline</button>
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="On the roster">
        {clubs.length === 0 ? (
          <EmptyNote text="You are not on any club roster. That is normal — plenty of athletes on Stride are unattached." />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {clubs.map((c) => (
              <Link key={c.slug} to={`/clubs/${c.slug}`} className="panel panel-hover flex items-center gap-3 p-4">
                <Avatar name={c.name} size={38} />
                <div className="min-w-0">
                  <div className="font-medium text-ink">{c.name}</div>
                  <div className="text-xs text-ink-3">{c.position || 'Member'}</div>
                </div>
                <Shield size={15} strokeWidth={1.9} className="ml-auto text-ink-3" />
              </Link>
            ))}
          </div>
        )}
      </Section>

      <Section title="Join a club"
               aside={<span className="meta">two ways in</span>}>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="panel p-4">
            <h4 className="font-medium text-ink">You were sent a link</h4>
            <p className="meta mt-1">
              A verified club can invite you directly. Redeeming their link vouches for you, so
              you skip the proof queue — the age and competition questions still apply.
            </p>
            <Link to="/athlete/application" className="btn mt-3 inline-block">Redeem an invite link</Link>
          </div>
          <div className="panel p-4">
            <h4 className="font-medium text-ink">You are looking for one</h4>
            <p className="meta mt-1">
              Browse clubs by sport and country, then message one from its page. A club has to
              invite you, and you have to accept — neither side can do it alone.
            </p>
            <Link to="/clubs" className="btn mt-3 inline-block">Browse clubs</Link>
          </div>
        </div>
      </Section>
    </div>
  )
}
