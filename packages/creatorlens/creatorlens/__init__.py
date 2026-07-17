"""CreatorLens — creator marketability console (prototype core).

Layers, each independently liftable into a larger app:
  connectors/  platform adapters (mock now, live later — same interface)
  ingestion/   sync pipeline: validated, retried, idempotent, audited
  analytics/   per-platform KPIs + 5-dimension marketability scoring
  api/         FastAPI surface + static operator console (web/)
"""

__version__ = "0.1.0"
FORMULA_VERSION = "0.1"
PLATFORMS = ("instagram", "youtube", "tiktok")
