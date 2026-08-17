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
  price_usd: number
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
  amount_usd: number
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
  base_rate_usd: number
  status: string
  claimed: boolean
  score: ScoreSummary | null
  affinity?: number
  reasons?: string[]
  following?: boolean
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
  amount_usd: number
  message: string
  status: 'offered' | 'accepted' | 'declined' | 'withdrawn' | 'completed'
  created_at: string
  responded_at: string | null
  campaign_name?: string
  category?: string
  org_name?: string
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
  budget_usd_min: number
  budget_usd_max: number
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
  base_rate_usd: number
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
    base_rate_usd: number
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
  club_backing: { amount_usd: number; status: string; created_at: string; package_name: string; club_name: string; org_name: string }[]
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

export const CATEGORIES = ['Sportswear', 'Nutrition', 'Technology', 'Automotive', 'Beverages', 'Finance', 'Travel', 'Wellness']

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
