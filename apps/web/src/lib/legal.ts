/** Legal and transparency copy.
 *
 *  Written against what the system actually does, not from a template: the
 *  cookie section names the one cookie the API sets, the data section mirrors
 *  the schema in apps/api/stride_api/db.py and packages/creatorlens/db.py, and
 *  the third-party section lists only providers the architecture actually
 *  names. When the schema changes, this file changes with it.
 *
 *  DRAFT STATUS: these are engineering-accurate drafts for review, not
 *  solicitor-reviewed instruments. docs/costs.md budgets $1–5k for that review
 *  before public launch. `LEGAL_STATUS` renders on every page so the state is
 *  never ambiguous to a reader.
 */

export const POLICY_VERSION = '2026-08-17'

export const LEGAL_STATUS =
  'Engineering-accurate draft, pending legal review before public launch. It describes exactly what the ' +
  'system does today — no clause here describes a feature that does not exist.'

export interface LegalSection {
  h: string
  p?: string[]
  list?: string[]
  table?: { head: string[]; rows: string[][] }
  note?: string
}

export interface LegalDoc {
  slug: string
  title: string
  eyebrow: string
  lede: string
  sections: LegalSection[]
}

const privacy: LegalDoc = {
  slug: 'privacy',
  title: 'Privacy Policy',
  eyebrow: 'Legal',
  lede:
    'What Stride collects, why, who can see it, and how to get it back or have it deleted. ' +
    'The short version: we hold your account, your own platform metrics, and aggregated audience ' +
    'statistics — never the identity of anyone who follows you.',
  sections: [
    {
      h: 'Who is responsible',
      p: [
        'Stride is the controller for the personal data described here. Until the operating entity is ' +
          'incorporated, the contact point is the project owner; the registered entity, address and ' +
          'representative will replace this paragraph before public launch.',
        'Spain-based operation means the LSSI-CE identification duties apply alongside the GDPR, which ' +
          'is why the operator identity is called out separately rather than buried in a contact form.',
      ],
    },
    {
      h: 'What we collect, and on what legal basis',
      table: {
        head: ['Data', 'Why', 'Lawful basis'],
        rows: [
          [
            'Email, display name, password hash (PBKDF2), role',
            'To create and secure your account',
            'Contract — Art. 6(1)(b)',
          ],
          [
            'Athlete or club profile: sport, country, bio, highlights, rate card, deal formats',
            'To present you to sponsors and in the public directory',
            'Contract — Art. 6(1)(b)',
          ],
          [
            'Connected platform metrics: follower counts, post reach and engagement, posting cadence',
            'To compute your marketability analytics',
            'Consent — Art. 6(1)(a), given per platform',
          ],
          [
            'Aggregated audience demographics: age bands, gender split, country shares',
            'To score audience fit against a campaign brief',
            'Consent — Art. 6(1)(a), given per platform',
          ],
          [
            'Deals, offers, package commitments and their status history',
            'To run the marketplace and keep a record both sides can rely on',
            'Contract — Art. 6(1)(b)',
          ],
          [
            'Audit events: sign-in, profile change, score computation, offer sent or answered',
            'Security, dispute resolution, and traceable analytics',
            'Legitimate interest — Art. 6(1)(f)',
          ],
          [
            'Request logs: method, path, status, duration, request ID, IP for rate limiting',
            'Keeping the service available and resisting abuse',
            'Legitimate interest — Art. 6(1)(f)',
          ],
        ],
      },
      note:
        'We do not collect special-category data, we do not buy data about you from third parties, and ' +
        'we do not profile you for advertising.',
    },
    {
      h: 'What we deliberately never receive',
      p: [
        'When you connect a social platform, Stride receives statistics about your audience — never the ' +
          'audience itself. The demographics table stores a dimension (age, gender or country), a bucket ' +
          '(“25-34”, “US”) and a share between 0 and 1. There is no row anywhere in the system that ' +
          'identifies an individual follower, because no such row is ever requested.',
        'That is a design decision, not a policy promise: the schema has nowhere to put it.',
      ],
    },
    {
      h: 'Who can see what',
      table: {
        head: ['Audience', 'Sees'],
        rows: [
          [
            'Sponsors',
            'Your public profile, marketability dimensions, per-platform inputs behind them, aggregated audience, recent post performance, and your rate card — for athletes listed as available',
          ],
          [
            'Clubs',
            'Roster membership and the packages they publish; a club never sees another club’s commercial data',
          ],
          [
            'Supporters (fans)',
            'Your public profile and marketability summary. Never rate cards, offers, earnings or any commercial internals',
          ],
          ['Other athletes', 'Exactly what a supporter sees'],
          ['Stride operators', 'The audit log, for security and dispute resolution. Not your password, which is stored only as a PBKDF2 hash'],
        ],
      },
      note:
        'Setting your profile to draft or hidden removes you from the directory and from sponsor matching. ' +
        'Every route enforces this server-side, not only in the interface.',
    },
    {
      h: 'Your rights',
      list: [
        'Access — a copy of everything held about you',
        'Rectification — correct anything wrong, most of it directly in your profile',
        'Erasure — delete your account and the data attached to it',
        'Portability — your profile and analytics in a machine-readable form',
        'Withdraw consent — disconnect any platform at any time; this stops future collection and removes that platform from your scores',
        'Object — to processing we base on legitimate interest',
        'Complain — to your national supervisory authority (in Spain, the AEPD)',
      ],
      note:
        'Disconnecting a platform is available today in your dashboard. Account export and deletion are ' +
        'built as an explicit flow rather than an email request — see “Your data”.',
    },
    {
      h: 'Retention',
      p: [
        'Account and profile data live until you delete the account. Deal records are kept while they may ' +
          'still be needed to resolve a dispute or meet accounting duties, and are then deleted or ' +
          'anonymised. Score snapshots and their evidence are the traceability the product is built on, ' +
          'so they persist while the account does and are removed with it. Request logs are short-lived.',
      ],
    },
    {
      h: 'Third parties and transfers',
      p: [
        'Stride connects to Instagram, YouTube and TikTok on your instruction. Those platforms are ' +
          'independent controllers for the data they hold about you, and their own terms and privacy ' +
          'policies apply to it.',
        'Infrastructure providers named in the architecture (database and authentication, hosting, ' +
          'transactional email, payments) act as processors under contract. The current iteration runs on ' +
          'simulated data and connects to no live platform API.',
      ],
    },
    {
      h: 'Children',
      p: [
        'Athletes under 18 are common in this market, which is exactly why it is called out rather than ' +
          'assumed away. Stride does not knowingly create accounts for anyone under 16 without verified ' +
          'parental consent, and commercial features — rate cards, offers, payouts — are gated behind ' +
          'adulthood or a verified guardian. This gate is specified and not yet implemented; it blocks ' +
          'public launch, not this draft.',
      ],
    },
    {
      h: 'Security',
      list: [
        'Passwords hashed with PBKDF2-SHA256 at 300,000 iterations, never stored or logged in the clear',
        'Sessions in an httpOnly, SameSite=Lax cookie the browser cannot read from JavaScript',
        'Every session invalidated immediately on demand by bumping a token version',
        'Role checks enforced on every API route, mirrored by database row-level security policies',
        'Rate limiting on credentials, request size caps, strict response headers, an API content policy of default-src none',
      ],
    },
  ],
}

const cookies: LegalDoc = {
  slug: 'cookies',
  title: 'Cookie Policy',
  eyebrow: 'Legal',
  lede:
    'Stride sets one cookie and stores one preference. Both are strictly necessary, so there is no ' +
    'consent banner and nothing to manage — an honest position we would rather explain than paper over ' +
    'with a dialog that does nothing.',
  sections: [
    {
      h: 'Everything stored on your device',
      table: {
        head: ['Name', 'Kind', 'Purpose', 'Lifetime'],
        rows: [
          [
            'stride_session',
            'Cookie — httpOnly, SameSite=Lax, Secure',
            'Keeps you signed in. Contains a signed session token and nothing else',
            'Session token TTL (12 hours by default), cleared on sign-out',
          ],
          [
            'stride-theme',
            'localStorage',
            'Remembers whether you chose the light or dark board, so the page does not flash the wrong one',
            'Until you clear site data',
          ],
        ],
      },
    },
    {
      h: 'Why there is no consent banner',
      p: [
        'The ePrivacy rules require consent for storage that is not strictly necessary. Both entries above ' +
          'are: one authenticates you, the other exists only because you clicked the theme control. ' +
          'Neither identifies you across sites, and neither is shared with anyone.',
        'Stride runs no analytics, loads no third-party scripts, embeds no social widgets, and serves its ' +
          'own fonts. There is no advertising identifier and no cross-site tracking, so a “manage cookies” ' +
          'dialog would offer a choice that does not exist.',
      ],
      note:
        'If Stride ever adds analytics or any non-essential storage, this page changes and a real consent ' +
        'control appears with it — refusing must stay as easy as accepting.',
    },
    {
      h: 'Managing them yourself',
      p: [
        'Signing out clears the session cookie. Your browser can block or clear both entries at any time; ' +
          'blocking the session cookie means you cannot stay signed in, which is the only thing it does.',
      ],
    },
  ],
}

const terms: LegalDoc = {
  slug: 'terms',
  title: 'Terms of Service',
  eyebrow: 'Legal',
  lede:
    'The agreement between you and Stride. It covers accounts, what we do and do not guarantee about ' +
    'analytics, and — importantly — that Stride is the marketplace, not a party to the sponsorship ' +
    'deals struck on it.',
  sections: [
    {
      h: 'Accounts',
      p: [
        'One role per account: athlete, club, sponsor, supporter. You are responsible for what happens ' +
          'under your credentials. Provide accurate information — a rate card or roster that misstates ' +
          'reality damages the counterparty who relied on it.',
      ],
    },
    {
      h: 'Your content and your analytics',
      p: [
        'Your profile, highlights and rate card remain yours. You grant Stride the licence needed to ' +
          'display them to the audiences described in the Privacy Policy and to compute analytics from ' +
          'connected platform data.',
        'Marketability scores are derived measurements, computed by a published and versioned formula set ' +
          'from the platform data you connect. They are an assessment, not a warranty of commercial ' +
          'outcome, and every score is decomposable into the inputs behind it precisely so it can be ' +
          'challenged.',
      ],
    },
    {
      h: 'Connecting a social platform',
      p: [
        'Connection is per platform, explicit, and revocable. When you connect one you confirm the account ' +
          'is yours and that you accept that platform’s own terms; Stride’s access is limited to the ' +
          'scopes shown at the moment you connect. Disconnecting stops collection and removes that ' +
          'platform from future scores.',
        'Where a platform’s developer terms require specific disclosure to you, that disclosure is shown ' +
          'at the point of connection rather than buried here.',
      ],
    },
    {
      h: 'Deals are between you and the counterparty',
      p: [
        'Stride surfaces matches, carries offers, and records what was agreed. The sponsorship contract ' +
          'itself is between the sponsor and the athlete or club. Stride is not the advertiser, not the ' +
          'talent agency, and not a party to the deal — it does not guarantee that an offer is made, ' +
          'accepted, performed or paid.',
        'Where Stride charges a fee on a transaction, that fee is stated before the transaction completes.',
      ],
    },
    {
      h: 'Disclosure of sponsored content',
      p: [
        'If you are paid to post, the law where your audience is generally requires you to say so — ' +
          'clearly, in the post itself. That duty is yours, not Stride’s, and no term here relieves you ' +
          'of it. Stride surfaces the obligation in the deal flow because a marketplace that stays quiet ' +
          'about it is not a neutral one.',
      ],
    },
    {
      h: 'What you may not do',
      list: [
        'Connect an account you do not control, or misrepresent whose audience it is',
        'Inflate metrics by artificial engagement, purchased followers, or any manipulation of the data Stride ingests',
        'Scrape, resell or redistribute another user’s analytics',
        'Use the platform to reach minors for commercial purposes outside the safeguards described in the Privacy Policy',
        'Probe or attack the service — responsible security reports are welcome and will not be pursued',
      ],
    },
    {
      h: 'Suspension and termination',
      p: [
        'You may close your account at any time. Stride may suspend an account that breaches these terms ' +
          'or that presents a security or fraud risk, and will say why unless prevented from doing so.',
      ],
    },
    {
      h: 'Liability and governing law',
      p: [
        'The service is provided as-is during this pre-launch phase. Nothing here limits liability that ' +
          'cannot lawfully be limited — including consumer rights, which are not waived by anything above. ' +
          'Governing law and jurisdiction follow the operating entity’s seat, to be stated on ' +
          'incorporation and expected to be Spain.',
      ],
    },
  ],
}

export const LEGAL_DOCS: LegalDoc[] = [privacy, cookies, terms]

export const legalDoc = (slug: string | undefined) => LEGAL_DOCS.find((d) => d.slug === slug)
