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

  /** Multipart, so it cannot go through `request`: setting Content-Type by
   *  hand on a FormData body drops the boundary the browser generates, and the
   *  server then sees one unparseable blob. Letting fetch set the header is the
   *  whole trick. */
  async upload<T>(path: string, file: File): Promise<T> {
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(path, { method: 'POST', credentials: 'same-origin', body: form })
    if (!res.ok) {
      let detail = res.statusText
      try {
        const data = await res.json()
        detail = typeof data.detail === 'string' ? data.detail : detail
      } catch { /* keep statusText */ }
      throw new ApiError(res.status, detail)
    }
    return res.json() as Promise<T>
  },
}

export const ERROR_TEXT: Record<string, string> = {
  unsupported_media_type: 'That file type is not supported — JPEG, PNG, WebP, GIF, MP4 or WebM.',
  content_does_not_match_its_type: 'That file is not the kind of image or video it claims to be.',
  empty_file: 'That file is empty.',
  invalid_credentials: 'Email or password is incorrect.',
  terms_not_accepted: 'You need to accept the Terms of Service and Privacy Policy to create an account.',
  invalid_or_expired_token: 'That link has already been used or has expired.',
  wrong_password: 'Your current password is not right.',
  confirmation_word_mismatch: 'Type DELETE to confirm.',
  cannot_message_this_person: 'You cannot message this person.',
  cannot_block_yourself: 'You cannot block yourself.',
  cannot_report_yourself: 'You cannot report yourself.',
  unknown_report_reason: 'Pick one of the listed reasons.',
  unknown_message: 'That message is not in a conversation you are part of.',
  already_resolved: 'This report has already been resolved.',
  account_suspended: 'This account has been suspended.',
  admin_accounts_are_removed_by_another_admin: 'An administrator account is removed by another administrator, not from here.',
  password_managed_elsewhere: 'This account signs in through an identity provider; change the password there.',
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
  payload_too_large: 'That is too large — uploads are capped at 8 MB.',
  session_revoked: 'Your session was signed out. Please sign in again.',
  already_backing_package: 'Your organization already backs this package.',
  already_on_roster: 'This athlete is already on your roster.',
  athlete_not_on_roster: 'Player-direct packages must name an athlete on your active roster.',
  player_direct_requires_athlete: 'Choose which roster athlete this package backs.',
  not_on_roster: 'This athlete is not on your active roster.',
  unknown_athlete: 'No athlete found with that handle.',
  unknown_campaign: 'That campaign does not exist, or it belongs to another organization.',
  campaign_not_active: 'This campaign is closed. Reopen it before sending offers.',
  unknown_campaign_status: 'A campaign is either active or closed.',
  website_must_be_a_url: 'A website has to start with http:// or https://.',
  no_sponsor_org: 'This account has no organization yet.',
  unknown_deal: 'That deal no longer exists.',
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
