"""TikTok connector.

Mock today. The live implementation uses the TikTok Display API (and Business API
where approved) — docs/real-api-mapping.md:
  fetch_account_snapshots -> GET /user/info/ ?fields=follower_count (self-collected daily history)
  fetch_posts             -> POST /video/list/ ?fields=view_count,like_count,comment_count,share_count,...
  fetch_demographics      -> Business API audience insights (gated; null demographics on Display-only access)
Scopes: user.info.stats, video.list.
"""

from ._mock import MockEngine, MockPlatformParams

PARAMS = MockPlatformParams(
    follower_range=(10_000, 2_000_000),
    reach_ratio_range=(0.10, 0.80),
    viral_sigma=0.85,  # the viral tail is the platform's signature
    er_benchmark=0.045,
    er_mult_range=(0.5, 2.0),
    cadence_range=(2.0, 7.0),
    content_types=[("video", 1.0)],
    engagement_split={"likes": 0.85, "comments": 0.07, "shares": 0.08, "saves": 0.0},
    watch_duration_range=(12.0, 38.0),
    video_types={"video"},
)


class MockTikTokConnector(MockEngine):
    def __init__(self):
        super().__init__("tiktok", PARAMS)
