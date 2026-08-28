/** Is there a page behind this string at all?
 *
 *  Structural only — scheme and host — and deliberately the same rule as
 *  `looks_openable` in `apps/api/stride_api/proofcheck.py`. The score an
 *  applicant is shown comes from the server, so a client that disagrees about
 *  what counts as a link tells them their evidence is fine while the scorer
 *  charges them the no-proof rate. `http://` is the case that matters: it
 *  passes a naive scheme test and has nothing behind it.
 */
export function openable(url: string): boolean {
  try {
    const parsed = new URL((url || '').trim())
    return (parsed.protocol === 'http:' || parsed.protocol === 'https:') && !!parsed.hostname
  } catch {
    return false
  }
}
