export const fmtNum = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return '—'
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(1) + 'M'
  if (Math.abs(n) >= 1e4) return (n / 1e3).toFixed(0) + 'K'
  if (Math.abs(n) >= 1e3) return (n / 1e3).toFixed(1) + 'K'
  return String(Math.round(n))
}

/** EUR, with comma grouping rather than the Spanish `1.234,56`.
 *
 *  The grouping is deliberate: every figure in business-plan/ is written this
 *  way, and a product whose interface and whose financial model disagree on
 *  where the separators go is harder to read across than one that picks a
 *  convention and keeps it. Revisit when the product is localised, which is a
 *  wider job than a separator. */
export const fmtMoney = (n: number | null | undefined): string =>
  n === null || n === undefined ? '—' : '€' + n.toLocaleString('en-US')

export const fmtPct = (x: number | null | undefined, dp = 1): string =>
  x === null || x === undefined ? '—' : (100 * x).toFixed(dp) + '%'

export const fmtDate = (ts: string | null | undefined): string => (ts ? ts.slice(0, 10) : '—')

export const fmtDT = (ts: string | null | undefined): string =>
  ts ? ts.replace('T', ' ').replace('Z', ' UTC') : '—'

export const initials = (name: string): string =>
  name.split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('')

/** Deterministic gradient pair per name — avatar identity without photos.
 *  Lightness is pinned low in both themes so the initials can always sit in a
 *  fixed light foreground; a theme-flipping text colour would fail contrast on
 *  one side or the other. */
export const avatarHue = (name: string): [string, string] => {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
  return [`hsl(${h} 40% 27%)`, `hsl(${(h + 45) % 360} 48% 17%)`]
}
