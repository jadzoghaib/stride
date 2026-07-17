"""Stride API — athlete monetization & sponsorship platform.

Layers:
  db.py            SQLite persistence (Postgres/Supabase-portable schema; see infra/supabase)
  auth.py          JWT sessions, PBKDF2 password hashing, role-based access control
  observability.py JSON logs, request IDs, Prometheus-format metrics
  chaos.py         failure injection for resilience drills
  matching.py      sponsor<->athlete matching on top of the CreatorLens analytics engine
  seed.py          simulated athletes/sponsors/fans (first-iteration data, by design)
  routers/         the API surface, one module per bounded context
"""

__version__ = "0.1.0"

ROLES = ("athlete", "sponsor", "fan", "club", "admin")
DEAL_TYPES = ("social_post", "event_appearance", "brand_ambassador", "content_creation", "product_collab")
DEAL_STATUSES = ("offered", "accepted", "declined", "withdrawn", "completed")
CATEGORIES = ("Sportswear", "Nutrition", "Technology", "Automotive", "Beverages", "Finance", "Travel", "Wellness")
REGIONS = ("Global", "Europe", "North America", "South America", "Asia-Pacific", "Middle East & Africa")
