/** "Your data" — the control surface a cookie banner is usually mistaken for.
 *
 *  Stride has no non-essential cookies to manage, but it does hold real personal
 *  data: connected-platform metrics and aggregated audience statistics. The
 *  meaningful controls are therefore about *platform consent and erasure*, not
 *  about storage on the device — so that is what this page exposes.
 *
 *  Each control states honestly whether it is live or specified, because a
 *  rights page that implies a button exists when it does not is worse than one
 *  that admits the gap.
 */

import { Link } from 'react-router-dom'
import { PageHeader, Section } from '../../components/ui'
import { useAuth } from '../../lib/auth'

interface Control {
  right: string
  article: string
  what: string
  status: 'live' | 'specified'
  where: string
}

const CONTROLS: Control[] = [
  {
    right: 'Withdraw consent',
    article: 'Art. 7(3)',
    what: 'Disconnect any social platform. Collection stops and that platform leaves your future scores.',
    status: 'live',
    where: 'Athlete dashboard → Connected platforms',
  },
  {
    right: 'Rectification',
    article: 'Art. 16',
    what: 'Edit your profile, rate card, deal formats and content themes directly.',
    status: 'live',
    where: 'Profile',
  },
  {
    right: 'Restrict processing',
    article: 'Art. 18',
    what: 'Set your profile to hidden — you leave the directory and sponsor matching without deleting anything.',
    status: 'live',
    where: 'Profile → Visibility',
  },
  {
    right: 'Access',
    article: 'Art. 15',
    what: 'A copy of everything held about you: account, profile, platform metrics, score snapshots and their evidence, deals, and your audit trail.',
    status: 'specified',
    where: 'Export — build before public launch',
  },
  {
    right: 'Portability',
    article: 'Art. 20',
    what: 'The same export in a machine-readable form, so your analytics history is not locked in.',
    status: 'specified',
    where: 'Export — build before public launch',
  },
  {
    right: 'Erasure',
    article: 'Art. 17',
    what: 'Delete the account and the data attached to it, with deal records retained only where accounting or dispute duties require.',
    status: 'specified',
    where: 'Delete account — build before public launch',
  },
]

export default function YourData() {
  const { me } = useAuth()

  return (
    <div className="max-w-3xl">
      <PageHeader
        eyebrow="Legal"
        title="Your data"
        lede="What Stride holds about you and the controls over it. Where a control is not built yet, this page says so rather than implying otherwise."
        aside={me ? <span className="tag capitalize">{me.role}</span> : undefined}
      />

      <Section title="What Stride holds">
        <div className="panel p-5">
          <p className="text-[15px] text-ink-2">
            Your account, your profile, the metrics from platforms you chose to connect, and
            aggregated statistics about your audience — age bands, gender split and country shares.
          </p>
          <p className="mt-3 text-[15px] text-ink-2">
            <b className="text-ink">Not the audience itself.</b> No row in this system identifies an
            individual follower, because no such data is ever requested from a platform. The
            demographics table can hold only a dimension, a bucket and a share.
          </p>
          <p className="meta mt-4">
            Full detail in the{' '}
            <Link to="/legal/privacy" className="text-accent-ink hover:underline">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </Section>

      <Section title="Your controls" aside={<span className="meta">3 of 6 live today</span>}>
        <div className="panel overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="table-head">Right</th>
                <th className="table-head">GDPR</th>
                <th className="table-head">What it does</th>
                <th className="table-head">Status</th>
              </tr>
            </thead>
            <tbody>
              {CONTROLS.map((c) => (
                <tr key={c.right}>
                  <td className="table-cell font-display font-semibold uppercase tracking-board text-ink">
                    {c.right}
                  </td>
                  <td className="table-cell meta whitespace-nowrap">{c.article}</td>
                  <td className="table-cell text-ink-2">
                    {c.what}
                    <span className="meta mt-1 block">{c.where}</span>
                  </td>
                  <td className="table-cell">
                    <span
                      className={`tag ${
                        c.status === 'live' ? 'border-ok/45 bg-ok/10 text-ok' : 'border-warn/45 bg-warn/10 text-warn'
                      }`}
                    >
                      {c.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Cookies">
        <div className="panel p-5">
          <p className="text-[15px] text-ink-2">
            One cookie keeps you signed in; one stored preference remembers your theme. Both are
            strictly necessary, so there is no consent banner and nothing to manage. Stride runs no
            analytics and loads nothing from a third party.
          </p>
          <p className="meta mt-3">
            The reasoning is set out in the{' '}
            <Link to="/legal/cookies" className="text-accent-ink hover:underline">
              Cookie Policy
            </Link>
            .
          </p>
        </div>
      </Section>
    </div>
  )
}
