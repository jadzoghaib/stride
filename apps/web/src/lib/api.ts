/** API client — same-origin via the Vite proxy (nginx in production), cookie sessions. */

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    credentials: 'same-origin',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data = await res.json()
      detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail ?? data)
    } catch {
      /* keep statusText */
    }
    // an expired/revoked session anywhere in the app returns to sign-in —
    // except the auth probe itself, which anonymous visitors hit legitimately
    if (res.status === 401 && path !== '/api/auth/me' &&
        ['not_authenticated', 'invalid_session', 'session_revoked', 'account_unavailable'].includes(detail)) {
      window.location.assign('/auth')
    }
    throw new ApiError(res.status, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body ?? {}),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
}

export const ERROR_TEXT: Record<string, string> = {
  invalid_credentials: 'Email or password is incorrect.',
  email_exists: 'An account with this email already exists.',
  offer_already_open: 'There is already an open offer to this athlete for this campaign.',
  deal_not_open: 'This deal has already been resolved.',
  deal_not_accepted: 'Accept the offer before attaching what you delivered.',
  no_deliverables: 'Attach at least one post before marking this delivered.',
  already_attached: 'That post is already attached to this deal.',
  unknown_post: 'That post is not on one of your connected accounts.',
  no_proof_to_check:
    'There is no link on this application, so there is nothing to check. Ask the applicant to supply one.',
  club_not_verified: 'Your club has to be verified before it can nominate athletes.',
  nomination_budget_exhausted:
    'You have nominated as many athletes as your declared roster allows. Update the roster size in your club application.',
  already_nominated: 'You have already nominated this athlete.',
  unknown_application: 'That application no longer exists.',
  unknown_club_application: 'That club has not applied yet.',
  unknown_competition_level: 'Pick one of the listed competition levels.',
  unknown_proof_kind: 'Pick one of the listed kinds of proof.',
  unknown_proof_status: 'Unknown proof status.',
  no_athlete_profile: 'This account has no athlete profile yet.',
  no_club: 'This account has no club yet.',
  already_connected: 'This platform is already connected.',
  consent_required: 'Connecting a platform needs your explicit consent to the data listed.',
  chaos_injected_failure: 'A simulated failure was injected (chaos drill in progress).',
  email_not_confirmed: 'Please confirm your email first — check your inbox for the confirmation link.',
  identity_provider_unreachable: 'The sign-in service is unreachable right now. Try again in a moment.',
  rate_limited: 'Too many attempts — wait a moment and try again.',
  payload_too_large: 'That request is too large.',
  session_revoked: 'Your session was signed out. Please sign in again.',
  already_backing_package: 'Your organization already backs this package.',
  already_on_roster: 'This athlete is already on your roster.',
  athlete_not_on_roster: 'Player-direct packages must name an athlete on your active roster.',
  player_direct_requires_athlete: 'Choose which roster athlete this package backs.',
  not_on_roster: 'This athlete is not on your active roster.',
  unknown_athlete: 'No athlete found with that handle.',
}

export function errorText(err: unknown): string {
  if (!(err instanceof ApiError)) return String(err)
  // `requires_role:a|b|c` is generated per route rather than drawn from a fixed
  // list, so it cannot live in ERROR_TEXT — it needs a prefix rule instead.
  // Without one the raw code reaches the screen, which is exactly what the
  // table exists to prevent.
  if (err.message.startsWith('requires_role:')) {
    return 'This account type does not have access to that page.'
  }
  return ERROR_TEXT[err.message] ?? err.message
}
