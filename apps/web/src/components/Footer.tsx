/** Site footer.
 *
 *  Deliberately NOT here: a "Manage cookies" control. Stride sets one strictly
 *  necessary cookie and stores one theme preference, so a consent manager would
 *  present a choice that does not exist — see the Cookie Policy, which explains
 *  that rather than hiding it. If non-essential storage is ever added, the
 *  control belongs here and the policy changes with it.
 *
 *  Also deliberately not here: "Terms of Use" alongside "Terms of Service".
 *  They are the same instrument under two names; shipping both is a tell that
 *  the footer was copied rather than written.
 */

import { Link } from 'react-router-dom'
import { POLICY_VERSION } from '../lib/legal'

const LINKS = [
  { to: '/legal/privacy', label: 'Privacy Policy' },
  { to: '/legal/cookies', label: 'Cookie Policy' },
  { to: '/legal/terms', label: 'Terms of Service' },
  { to: '/legal/data', label: 'Your Data' },
]

export default function Footer() {
  return (
    /* No top margin: inside the Shell, `.stride-main` already reserves 76px
       below the content, and on the landing page the block above brings its
       own spacing. Adding margin here stacked the two into ~156px of dead
       band. */
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-page flex-wrap items-center gap-x-6 gap-y-3 px-7 py-7">
        <nav className="flex flex-wrap items-center gap-x-5 gap-y-2">
          {LINKS.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="font-display text-fine font-semibold uppercase tracking-micro text-ink-3 transition-colors hover:text-ink"
            >
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex flex-wrap items-center gap-x-4 gap-y-1">
          <span className="meta">policies v{POLICY_VERSION}</span>
          <span className="meta">© {new Date().getFullYear()} Stride. All rights reserved.</span>
        </div>
      </div>
    </footer>
  )
}
