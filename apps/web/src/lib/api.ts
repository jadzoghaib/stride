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
  already_connected: 'This platform is already connected.',
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
  unknown_athlete: 'No listed athlete found with that handle.',
}

export function errorText(err: unknown): string {
  if (err instanceof ApiError) return ERROR_TEXT[err.message] ?? err.message
  return String(err)
}
