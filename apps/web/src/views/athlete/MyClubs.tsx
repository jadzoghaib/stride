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
import { Avatar, EmptyNote, LoadError, MessageButton, Modal, PageHeader, PageLoading, Section } from '../../components/ui'
import { api, errorText } from '../../lib/api'
import { useToast } from '../../lib/toast'
import type { AthleteWorkspace, ClubInvitation } from '../../types'

export default function MyClubs() {
  const [ws, setWs] = useState<AthleteWorkspace | null>(null)
  const [invites, setInvites] = useState<ClubInvitation[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [detail, setDetail] = useState<ClubInvitation | null>(null)
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
                {i.player_direct_for_me > 0 ? (
                  // Said first, because it is the fact that changes the answer:
                  // this club is already selling sponsorship built around you.
                  <p className="meta max-w-md text-warn">
                    They already list {i.player_direct_for_me} package
                    {i.player_direct_for_me === 1 ? '' : 's'} built around you — those only become
                    sellable if you accept.
                  </p>
                ) : (
                  <p className="meta max-w-md">
                    Joining lets them build sponsorship packages around you, and vouch for you in
                    admission. You can leave later.
                  </p>
                )}
                {/* Accept, decline, read the detail, or ask them something —
                    an invitation is a request, and a request you can only
                    answer yes or no to is an ultimatum. */}
                <div className="ml-auto flex flex-wrap gap-2">
                  <button className="btn-go px-3 py-1.5 text-xs" disabled={busy === i.invitation_id}
                          onClick={() => void respond(i, 'accept')}>Accept</button>
                  <button className="btn px-3 py-1.5 text-xs" disabled={busy === i.invitation_id}
                          onClick={() => void respond(i, 'decline')}>Decline</button>
                  <button className="btn px-3 py-1.5 text-xs"
                          onClick={() => setDetail(i)}>See details</button>
                  {i.club_user_id != null && (
                    <MessageButton to={{ user: i.club_user_id }} name={i.name} label="Ask" />
                  )}
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

      {detail && (
        <Modal title={detail.name} onClose={() => setDetail(null)}>
          {() => (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-2">
                <Fact label="Sport" value={detail.sport} />
                <Fact label="Based" value={[detail.region, detail.country].filter(Boolean).join(', ') || '—'} />
                <Fact label="Athletes on the roster" value={String(detail.roster_count)} />
                <Fact label="Sponsorship packages" value={String(detail.package_count)} />
              </div>

              {detail.position && (
                <p className="text-sm text-ink-2">
                  They are inviting you as <strong className="text-ink">{detail.position}</strong>.
                </p>
              )}

              {detail.bio && (
                <div>
                  <h4 className="cap mb-1.5 text-ink-3">About the club</h4>
                  <p className="text-sm text-ink-2">{detail.bio}</p>
                </div>
              )}

              <div>
                <h4 className="cap mb-1.5 text-ink-3">What accepting changes</h4>
                <ul className="space-y-1.5 text-sm text-ink-2">
                  <li>— They can publish sponsorship packages built around you, and sell them.</li>
                  <li>— They can vouch for you in admission, which skips the proof queue.</li>
                  <li>— You appear on their public roster. You can leave later.</li>
                </ul>
                {detail.player_direct_for_me > 0 && (
                  <p className="meta mt-2 text-warn">
                    {detail.player_direct_for_me} package{detail.player_direct_for_me === 1 ? '' : 's'} built
                    around you {detail.player_direct_for_me === 1 ? 'is' : 'are'} already listed and cannot
                    be sold unless you accept.
                  </p>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2 border-t border-line pt-3">
                <Link to={`/clubs/${detail.slug}`} className="btn px-3 py-1.5 text-xs">
                  Open their page
                </Link>
                {detail.club_user_id != null && (
                  <MessageButton to={{ user: detail.club_user_id }} name={detail.name}
                                 label={`Ask ${detail.name} a question`} />
                )}
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* One path, not two. These were presented as alternatives — "you were
          sent a link" beside "you are looking for one" — but they are the same
          route at different points along it: you find a club, you talk to them,
          and if it goes well they send you a link. Messaging a club needs no
          prior relationship, so the conversation is the way in and redeeming is
          what happens at the end of it. */}
      <Section title="Join a club">
        <div className="panel p-4">
          <p className="text-sm text-ink-2">
            Find a club in the directory and message them — you do not need an introduction, and
            they can write back. If it goes somewhere they will send you an invite link, which
            vouches for you and skips the proof queue. A club has to invite you and you have to
            accept; neither side can do it alone.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to="/clubs" className="btn-go px-3 py-1.5 text-xs">Browse clubs</Link>
            <Link to="/athlete/application" className="btn px-3 py-1.5 text-xs">
              I already have a link
            </Link>
          </div>
        </div>
      </Section>
    </div>
  )
}


function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-line bg-raised px-3 py-2.5">
      <div className="cap text-ink-3">{label}</div>
      <div className="tnum mt-0.5 text-sm text-ink-2">{value}</div>
    </div>
  )
}
