# Reference repo analysis — IOC-NIL-Monetization-Platform_DPM → Stride

Analyzed at github.com/jadzoghaib/IOC-NIL-Monetization-Platform_DPM (React 18 + Vite +
Tailwind + framer-motion frontend; FastAPI backend; JSON athlete data; localStorage store).

## Reused (patterns and product structure)
- **The three-mode product** (fan / athlete / business) → Stride's three account types,
  now real roles with auth instead of a mode switcher.
- **View inventory**: business discover → athlete detail → campaign builder → offers;
  athlete onboarding/dashboard/manage; fan discover/feed. All carried over, generalized.
- **Domain vocabulary**: deal types, budget bands, categories, region lists (store.ts).
- **Explainable matching** ("reasons" attached to every match) — the concept kept,
  the scoring engine replaced.
- **Stack**: React + Vite + TS + Tailwind + lucide-react + FastAPI — same bones,
  so your existing familiarity transfers.

## Changed
- **localStorage store → SQLite/Postgres + real API.** The old store.ts docstring
  itself declared this the intended upgrade path.
- **Mode switching → real auth**: JWT sessions, PBKDF2 hashing, role-based access
  control on every route; Supabase-ready schema + RLS migration included.
- **Matching**: the old additive heuristic (+50 country, +15 medalist, emoji reasons)
  becomes a weighted component model where analytics components come from the
  CreatorLens engine and every match decomposes into weight × component.
- **UI register**: emoji-heavy consumer look → dark, editorial, no emojis,
  gradient waves as controlled accents.

## Generalized beyond Olympic athletes
- Games picker (paris_2024/milan_2026), medals, flagbearers, IOC partner archetypes,
  Olympic rings — all removed as core concepts. Medals → free-form career highlights;
  sports open-ended; sponsors are arbitrary orgs with industries.

## Rebuilt from scratch
- **`business_metrics.py` — the most important replacement.** The old file fabricated
  reach/engagement estimates from md5-seeded randomness ("no real social data is
  available"). Stride replaces it with the CreatorLens analytics engine (built earlier
  in this project): a real ingestion pipeline, versioned scoring formulas, evidence and
  coverage on every number. Mock connectors today, but the *structure* is production.
- Persistence, auth, observability, deployment artifacts — none existed.

## Moved to the sponsor side
- Athlete evaluation (scores, audience, posts) is now sponsor-facing evidence.
- Campaign briefs create CreatorLens sponsor targets; audience fit is computed
  per campaign, not globally.
- Offer creation, withdrawal, pipeline tracking.

## Stayed on the athlete side
- Profile management, rate card, deal formats, visibility control (draft/listed/hidden).
- Platform connections + the same analytics the sponsor sees (information symmetry).
- Deal inbox with accept/decline.

## General user (fan) mode
- Interest-based discovery with explained affinity ranking (the old quiz concept,
  compressed into interest chips), follows, and a following feed showing trajectory.
- Old fan quiz/AI-assistant/share-cards: postponed, not deleted conceptually
  (see build-plan.md Phase 3).

## Explicitly dropped
- OpenRouter AI assistant (unfocused for this draft), GSAP/framer-motion animation
  layers (the new register is calmer), Wikipedia/Wikidata enrichment scripts
  (real-data ingestion returns in a later phase behind the connector interface).
