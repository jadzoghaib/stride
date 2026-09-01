export interface Me {
  id: number
  email: string
  role: 'athlete' | 'sponsor' | 'fan' | 'club' | 'admin'
  display_name: string
  athlete_profile?: { id: number; slug: string; status: string } | null
  org?: { id: number; name: string; industry: string } | null
  club?: { id: number; slug: string; name: string; status: string } | null
}

export interface Club {
  id: number
  slug: string
  name: string
  sport: string
  country: string
  region: string
  bio: string
  status: string
  member_count: number
  package_count: number
  backer_count: number
}

export interface ClubPackage {
  id: number
  club_id: number
  athlete_id: number | null
  name: string
  description: string
  package_type: 'club' | 'player_direct'
  price_eur: number
  perks: string[]
  status: 'active' | 'archived'
  created_at: string
  athlete_name?: string | null
  athlete_slug?: string | null
  active_backers: number
}

export interface RosterMember {
  membership_id: number
  position: string
  membership_status: string
  joined_at: string
  athlete_id: number
  slug: string
  display_name: string
  sport: string
  country: string
}

export interface Commitment {
  id: number
  package_id: number
  org_id: number
  amount_eur: number
  status: 'active' | 'cancelled'
  created_at: string
  cancelled_at: string | null
  package_name?: string
  package_type?: string
  club_name?: string
  club_slug?: string
  athlete_name?: string | null
  org_name?: string
}

export interface ClubWorkspace {
  club: Club
  editable: { name: string; sport: string; country: string; region: string; bio: string; status: string }
  roster: RosterMember[]
  packages: ClubPackage[]
  commitments: Commitment[]
  revenue_active: number
}

export interface ScoreSummary {
  computed_at: string
  dimensions: Record<string, number | null>
  coverage: { connected: number; total: number; list: string[]; missing: string[] }
}

export interface AthletePublic {
  id: number
  slug: string
  display_name: string
  sport: string
  country: string
  region: string
  bio: string
  career_highlights: string[]
  topics: string[]
  deal_types: string[]
  status: string
  claimed: boolean
  /** Where to find them off Stride. Everyone gets these. */
  socials: { platform: string; handle: string; url: string }[]
  /** Sales material: the asking price and the evidence behind it. Present only
   *  for a sponsor, a club, an admin, or the athlete reading their own profile
   *  — which is why both are optional rather than nullable. A fan is buying a
   *  post, not the athlete's audience. */
  base_rate_eur?: number
  score?: ScoreSummary | null
  affinity?: number
  reasons?: string[]
  /** follow = their free posts and their platform news.
   *  subscribe = the posts they marked subscribers-only. */
  /** Audience size. Social proof, not sales material — every creator page
   *  in the category shows it, and a fan reads it as "is this worth my
   *  time" rather than "what does this person cost". */
  followers?: number
  subscribers?: number
  following?: boolean
  subscribed?: boolean
  /** The server decides, so the envelope cannot appear where the send
   *  would be refused — and it is false for an unclaimed profile, which
   *  has no inbox to deliver to. */
  can_message?: boolean
  audience?: Record<string, Record<string, number>>
  score_history?: { computed_at: string; audience_scale: number | null }[]
  clubs?: { name: string; slug: string; position: string }[]
}

export interface Deal {
  id: number
  campaign_id: number
  org_id: number
  athlete_id: number
  deal_type: string
  amount_eur: number
  message: string
  status: 'offered' | 'accepted' | 'declined' | 'withdrawn' | 'completed'
  created_at: string
  responded_at: string | null
  completed_at?: string | null
  projected_reach?: number | null
  /** Posts the athlete has already attached as proof of delivery. Present on
   *  the athlete's own workspace only — a sponsor reads these through
   *  `DealPerformance` instead. */
  deliverable_post_ids?: number[]
  campaign_name?: string
  category?: string
  org_name?: string
  /** The campaign's own terms, sent with the offer so the athlete can read what
   *  they are being asked to join before answering it. */
  objective?: string | null
  org_industry?: string | null
  org_website?: string | null
  /** The sponsor's user, which is what `POST /api/messages` addresses. */
  org_user_id?: number | null
  target_countries?: string[]
  target_age_buckets?: string[]
  target_genders?: string[]
  target_topics?: string[]
  budget_eur_min?: number | null
  budget_eur_max?: number | null
  athlete_name?: string
  athlete_slug?: string
  sport?: string
}

export interface Campaign {
  id: number
  org_id: number
  name: string
  objective: string
  category: string
  deal_types: string[]
  budget_eur_min: number
  budget_eur_max: number
  target_age_buckets: string[]
  target_genders: string[]
  target_countries: string[]
  target_topics: string[]
  sponsor_target_id: number | null
  status: string
  created_at: string
}

export interface Match {
  athlete_id: number
  slug: string
  display_name: string
  sport: string
  country: string
  base_rate_eur: number
  score: number
  /** null = the dimension could not be measured. It is excluded from the score
   *  rather than counted as zero, so never render it as a 0. */
  components: Record<string, number | null>
  /** The nominal model — what each component is worth when everything is measured. */
  weights: Record<string, number>
  /** What actually produced this score: `weights` renormalised over the measured
   *  components. Multiply by the component to get its real contribution. */
  effective_weights: Record<string, number | null>
  reasons: string[]
  caveats: string[]
  analytics_summary: {
    dimensions: Record<string, number | null>
    coverage: { connected: number; total: number; missing: string[] }
  } | null
}

/** A post the athlete can attach to a deal as proof of delivery. */
export interface AthletePost {
  post_id: number
  platform: string
  title: string
  published_at: string
  reach: number | null
}

/** What the sponsor actually got. Every headline figure decomposes to
 *  `deliverables` — the same rule the marketability scores follow. */
export interface DealPerformance {
  deal: {
    id: number
    status: Deal['status']
    deal_type: string
    amount_eur: number
    created_at: string
    responded_at: string | null
    completed_at: string | null
    athlete_name: string
    athlete_slug: string
    campaign_name: string
  }
  deliverables: {
    post_id: number
    platform: string
    title: string
    published_at: string
    permalink: string
    // null when the post is attached but its metrics have not been captured —
    // `fmtNum` renders that as a dash, which is the truth about it
    reach: number | null
    engagement_rate: number | null
  }[]
  // null until something is attached *and measured*: nothing delivered is not
  // the same measurement as nobody reached
  delivered: { posts: number; reach: number | null; engagements: number | null }
  projected: { reach: number | null }
  variance_pct: number | null
  cost_per_1k_reach: number | null
  cost_per_engagement: number | null
}

export interface PlatformAccount {
  id: number
  platform: string
  handle: string
  connection_status: string
  last_synced_at: string | null
  followers: number | null
  last_run: { status: string; finished_at: string; error: string | null } | null
}

export interface AthleteWorkspace {
  profile: AthletePublic
  editable: {
    display_name: string
    sport: string
    country: string
    region: string
    bio: string
    base_rate_eur: number
    status: string
    career_highlights: string[]
    topics: string[]
    deal_types: string[]
  }
  accounts: PlatformAccount[]
  analytics: {
    dimensions: Record<string, number | null>
    coverage: { platforms: ScoreSummary['coverage']; dimensions: Record<string, { confidence: string | null; data_points?: number; unit?: string; reason?: string }> }
    inputs: { platform_kpis: Record<string, Record<string, number | null>>; intermediate: Record<string, unknown> }
    computed_at: string
    formula_version: string
  } | null
  audience: Record<string, Record<string, number>>
  deals: Deal[]
  earnings: number
  clubs: { name: string; slug: string; position: string }[]
  club_backing: { amount_eur: number; status: string; created_at: string; package_name: string; club_name: string; org_name: string }[]
}

export const DIMENSIONS = [
  { key: 'audience_scale', label: 'Audience Scale' },
  { key: 'engagement_quality', label: 'Engagement Quality' },
  { key: 'audience_fit', label: 'Audience Fit' },
  { key: 'growth', label: 'Growth' },
  { key: 'consistency', label: 'Consistency' },
] as const

export const DEAL_TYPES = [
  { key: 'social_post', label: 'Social Post' },
  { key: 'event_appearance', label: 'Event Appearance' },
  { key: 'brand_ambassador', label: 'Brand Ambassador' },
  { key: 'content_creation', label: 'Content Creation' },
  { key: 'product_collab', label: 'Product Collaboration' },
] as const

// 'Other' last, and deliberately: a fixed list with no escape hatch makes a
// sponsor pick the nearest wrong answer, which then poisons category-based
// matching for every athlete it touches.
export const CATEGORIES = ['Sportswear', 'Nutrition', 'Technology', 'Automotive',
  'Beverages', 'Finance', 'Travel', 'Wellness', 'Other']

export const dealTypeLabel = (key: string) =>
  DEAL_TYPES.find((d) => d.key === key)?.label ?? key.replace(/_/g, ' ')

/** Platforms are stored lowercase. CSS `capitalize` renders "Youtube" and
 *  "Tiktok", which are not the brands' names — these are, so use this anywhere
 *  a platform is shown in sentence case. (Uppercase table cells are unaffected.) */
const PLATFORM_LABELS: Record<string, string> = {
  instagram: 'Instagram',
  youtube: 'YouTube',
  tiktok: 'TikTok',
}

export const platformLabel = (key: string) =>
  PLATFORM_LABELS[key] ?? key.charAt(0).toUpperCase() + key.slice(1)

/** The API computes no athlete-level composite — the only `score` it produces is
 *  per sponsor campaign. Any headline marketability figure is therefore derived
 *  here, and every caller must label it as a mean of `n` dimensions so it is
 *  never mistaken for a stored value. Returns null when nothing is computed. */
export function meanScore(dimensions: Record<string, number | null> | undefined | null) {
  if (!dimensions) return { value: null as number | null, n: 0 }
  const values = DIMENSIONS.map((d) => dimensions[d.key]).filter(
    (v): v is number => typeof v === 'number',
  )
  if (!values.length) return { value: null as number | null, n: 0 }
  return { value: values.reduce((s, v) => s + v, 0) / values.length, n: values.length }
}


/* ── Admission ──────────────────────────────────────────────────────────────
 *  The gate, and its decomposition. Every field the server returns is here for
 *  one reason: a decision an applicant cannot have explained to them is a
 *  decision they cannot act on, so the interface shows the whole working. */

export const COMPETITION_LEVELS = ['local', 'regional', 'national', 'international'] as const
export const PROOF_KINDS = ['none', 'roster', 'results', 'licence'] as const

export type AdmissionDecision = 'pending' | 'admitted' | 'review' | 'rejected'
export type ProofStatus = 'unverified' | 'pending' | 'verified' | 'rejected'

export interface AthleteApplication {
  id: number
  athlete_id: number
  discipline: string
  club_name: string
  league_name: string
  competition_level: string
  years_competing: number | null
  birth_year: number | null
  proof_url: string
  proof_kind: string
  proof_status: ProofStatus
  nominated_by_club: number | null
  credibility: number | null
  decision: AdmissionDecision
  decision_rule: string
  admitted_via: string
  policy_version: string
  submitted_at: string
  decided_at: string | null
  /** joined in on the admin queue only */
  slug?: string
  display_name?: string
  sport?: string
  country?: string
  scored?: Credibility
}

/** What the scorer returns: the number, and everything behind it. */
export interface Credibility {
  credibility: number
  claim: number
  components: Record<string, number | null>
  weights: Record<string, number>
  missing: string[]
  scoreable: boolean
  evidence_multiplier: number
  reasons: string[]
  caveats: string[]
  policy_version: string
}

/** A scored application plus the verdict — what every write endpoint returns. */
export interface AdmissionVerdict extends Credibility {
  decision: AdmissionDecision
  rule: string
  effective_credibility: number
  notes: string[]
  thresholds: { admit: number; review: number }
  listing: string
  social_score: number | null
}

export interface AthleteApplicationView {
  /** Set when the club that vouched for this athlete withdrew it. There are
   *  exactly two ways out and the page has to name both. */
  frozen?: { at: string; club: string | null } | null
  application: AthleteApplication | null
  scored?: Credibility
  club_floor?: number
  thresholds?: { admit: number }
}

export interface ClubApplication {
  id: number
  club_id: number
  legal_name: string
  registration_id: string
  federation_name: string
  federation_id: string
  founded_year: number | null
  competition_level: string
  teams_count: number | null
  registered_athletes: number
  roster_url: string
  proof_kind: string
  proof_status: ProofStatus
  legitimacy: number | null
  decision: 'pending' | 'verified' | 'review' | 'rejected'
  policy_version: string
  submitted_at: string
  decided_at: string | null
  /** joined in on the admin queue only */
  slug?: string
  name?: string
  sport?: string
  country?: string
  scored?: ClubLegitimacy
}

export interface ClubLegitimacy {
  legitimacy: number
  claim: number
  decision: 'pending' | 'verified' | 'review' | 'rejected'
  components: Record<string, number | null>
  weights: Record<string, number>
  missing: string[]
  evidence_multiplier: number
  nomination_floor: number
  reasons: string[]
  caveats: string[]
  thresholds: { verify: number; review: number }
  policy_version: string
}

export interface ClubApplicationView {
  application: ClubApplication | null
  scored?: ClubLegitimacy
  nominations?: { used: number; budget: number }
}

/** Rule codes, said in words the applicant can act on. The server returns a
 *  machine-readable rule precisely so the wording lives here and can change
 *  without touching the policy. */
export const DECISION_COPY: Record<string, string> = {
  credibility_above_admit: 'Admitted. Your profile can be listed for sponsors.',
  credibility_in_review_band: 'With our team for a look.',
  evidence_not_checked:
    'Your claim clears the bar — we just have not opened your proof link yet.',
  incomplete_application:
    'Not submitted yet. Competition level is missing, and nothing can be assessed without it.',
  under_minimum_age: 'Stride accounts are 16 and over.',
  proof_rejected: 'We checked your link and it did not support the claim.',
  credibility_below_review: 'Not enough evidence yet to assess this.',
  social_reach_without_credibility:
    'Sent for a human look: a large following behind a claim we cannot yet verify.',
  club_verification_revoked:
    'Your club lost its verification, so this is back with our team.',
}

export const componentLabel = (key: string) =>
  ({
    level: 'Competition level',
    tenure: 'Seasons competing',
    registration: 'Legal registration',
    federation: 'Federation affiliation',
    longevity: 'Years operating',
    structure: 'Teams fielded',
    roster_proof: 'Public roster',
  })[key] ?? key.replace(/_/g, ' ')

export const proofStatusLabel = (status: string) =>
  ({
    unverified: 'not checked',
    pending: 'queued for checking',
    verified: 'checked',
    rejected: 'checked — did not stand up',
  })[status] ?? status


/** The directory is paged: a keyset cursor, not an offset, because the listed
 *  set shifts every time an athlete is admitted or delisted. */
export interface Facets {
  sports: string[]
  countries: string[]
  /** ISO codes — the buckets audience demographics use, and the only thing
   *  campaign targeting can be compared against. Not the same vocabulary as
   *  `countries`, which are profile countries as full names. */
  audience_countries: string[]
  topics: string[]
}

export interface AthletePage {
  athletes: AthletePublic[]
  next_cursor: string | null
  limit: number
}

export interface MatchesResponse {
  campaign: Campaign
  matches: Match[]
  ranked_total: number
  slate_id: string
  duration_ms: number
  recorded?: boolean
}

// ── content ─────────────────────────────────────────────────────────────────

/** A post the athlete made on one of their own platforms, surfaced on their
 *  wall. Deliberately carries no metrics: reach is the athlete's analytics and
 *  the sponsor's evidence, and a fan gets the post, not the numbers behind it. */
export interface NewsItem {
  platform: string
  title: string
  published_at: string
  permalink: string
  content_type: string
  /** Present on the follower feed, where posts from several athletes are mixed
   *  together. Absent on an athlete's own page, where the whole page says who
   *  wrote them. */
  author?: string
  author_slug?: string
}

export interface ContentItem {
  id: number
  kind: 'post' | 'course' | 'session' | 'event' | 'product' | 'poll'
  title: string
  body: string
  min_tier: string
  tier_label: string
  label: '' | 'sponsored' | 'highlighted'
  sponsor_name: string
  part_of: number | null
  position: number | null
  starts_at: string | null
  location: string
  capacity: number | null
  /** A picture or a clip, by link. Withheld with the body when locked, so
   *  `has_media` is how a locked card knows to show a lock panel at all. */
  media_url: string
  media_kind: '' | 'image' | 'video'
  has_media?: boolean
  poll?: {
    total: number
    voted: number | null
    options: { id: number; label: string; votes: number; share: number }[]
  } | null
  /** Products only: where the thing is actually sold. Stride never takes the
   *  money, so this is the whole point of the row. */
  external_url: string
  status: 'draft' | 'published'
  published_at: string | null
  /** True when the reader's tier is below `min_tier`. The body is empty then;
   *  everything else stays, so a fan can decide whether it is worth paying for. */
  locked: boolean
  author?: string
  author_slug?: string
}

export interface ClubInvitation {
  invitation_id: number
  position: string
  invited_at: string
  club_id: number
  slug: string
  name: string
  sport: string
  country: string
}

export const CONTENT_KINDS = ['post', 'course', 'session', 'event', 'product', 'poll'] as const
/** The scarce kinds: they cost the author a day, so they carry a date, a place
 *  and a capacity — and they are the argument for the top tier. */
export const SCHEDULED_KINDS = ['session', 'event'] as const
export const CONTENT_TIERS = [
  { value: '', label: 'Everyone' },
  { value: 'supporter', label: 'Subscribers only' },
] as const
export const CONTENT_LABELS = [
  { value: '', label: 'None' },
  { value: 'sponsored', label: 'Sponsored — a brand paid for this' },
  { value: 'highlighted', label: 'Highlighted — feature it' },
] as const
