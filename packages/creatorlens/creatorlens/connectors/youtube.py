"""YouTube connector.

Mock today. The live implementation uses YouTube Data API v3 + Analytics API v2
(docs/real-api-mapping.md):
  fetch_account_snapshots -> Analytics reports.query (subscribersGained/Lost, views by day) + channels.list statistics
  fetch_posts             -> uploads playlist + videos.list + Analytics per-video (views, watch time, avg duration, likes, comments)
  fetch_demographics      -> Analytics viewerPercentage by ageGroup/gender, views by country
Scopes: youtube.readonly, yt-analytics.readonly.

Note: YouTube has no "reach" — views serve as the reach proxy (reach == views here),
which is how the KPI layer treats the column for this platform.
"""

from ._mock import MockEngine, MockPlatformParams

PARAMS = MockPlatformParams(
    follower_range=(5_000, 1_500_000),
    reach_ratio_range=(0.15, 0.90),  # views per video relative to subscribers
    viral_sigma=0.55,
    er_benchmark=0.035,
    er_mult_range=(0.4, 1.8),
    cadence_range=(0.5, 2.5),
    content_types=[("video", 0.75), ("short", 0.25)],
    engagement_split={"likes": 0.90, "comments": 0.09, "shares": 0.01, "saves": 0.0},
    watch_duration_range=(90.0, 320.0),
    video_types={"video", "short"},
)


class MockYouTubeConnector(MockEngine):
    def __init__(self):
        super().__init__("youtube", PARAMS)
