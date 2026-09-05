/** The banner behind a profile.
 *
 *  Drawn rather than uploaded. A creator page needs a cover or the header
 *  collapses into a name on a flat background, and twenty-four athletes with
 *  no art department would otherwise all look identical. The palette comes
 *  from `avatarHue`, so a person's cover and their avatar are the same colour
 *  story, and the amber rule and contour lines are the board motif the rest of
 *  the product is drawn with — the same reason the dashboards look related.
 *
 *  Deterministic on the name: reloading does not reshuffle anybody.
 */
import { useState } from 'react'
import { avatarHue } from '../lib/format'

export function Cover({ name, height = 'h-44 md:h-56', src }: {
  name: string
  height?: string
  /** An uploaded banner. Empty keeps the drawn one — the whole point of the
   *  generated art is that nobody has to supply a photograph to have a page
   *  worth looking at. A broken link falls back to it too. */
  src?: string | null
}) {
  const [near, far] = avatarHue(name)
  const [broken, setBroken] = useState(false)

  if (src && !broken) {
    return (
      <div className={`relative w-full overflow-hidden ${height}`}>
        <img src={src} alt="" onError={() => setBroken(true)}
             className="h-full w-full object-cover" />
        {/* the amber rule stays: it is the seam the avatar sits on, and the
            header reads as two stacked blocks without it */}
        <div className="absolute inset-x-0 bottom-0 h-1 bg-accent" />
      </div>
    )
  }

  // A second stable number off the same name, so the contours differ per person
  let seed = 0
  for (const c of name) seed = (seed * 17 + c.charCodeAt(0)) % 1000
  const lift = 40 + (seed % 60)

  return (
    <div className={`relative w-full overflow-hidden ${height}`} aria-hidden="true">
      <svg className="h-full w-full" viewBox="0 0 1200 320" preserveAspectRatio="xMidYMid slice">
        <defs>
          <linearGradient id={`cv-${seed}`} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor={near} />
            <stop offset="100%" stopColor={far} />
          </linearGradient>
        </defs>
        <rect width="1200" height="320" fill={`url(#cv-${seed})`} />
        <g fill="none" stroke="#ffffff" strokeOpacity="0.09" strokeWidth="2">
          <path d={`M0 ${200 + lift} C 220 ${120 + lift}, 380 ${240 + lift}, 600 ${160 + lift}
                    S 980 ${60 + lift}, 1200 ${120 + lift}`} />
          <path d={`M0 ${250 + lift} C 240 ${170 + lift}, 400 ${290 + lift}, 620 ${210 + lift}
                    S 1000 ${110 + lift}, 1200 ${170 + lift}`} />
        </g>
        <circle cx={980 + (seed % 90)} cy={90} r={54} fill="rgb(var(--c-accent))" fillOpacity="0.9" />
        <rect x="0" y="316" width="1200" height="4" fill="rgb(var(--c-accent))" />
      </svg>
    </div>
  )
}
