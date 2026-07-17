"""Instagram connector.

Mock today. The live implementation replaces MockEngine calls with Meta Graph
API requests — endpoint-by-endpoint mapping in docs/real-api-mapping.md:
  fetch_account_snapshots -> GET /{ig-user-id}?fields=followers_count (+ insights reach/profile_views, period=day)
  fetch_posts             -> GET /{ig-user-id}/media + GET /{ig-media-id}/insights?metric=reach,impressions,likes,comments,shares,saved
  fetch_demographics      -> GET /{ig-user-id}/insights?metric=follower_demographics&breakdown=age,gender,country
Scopes: instagram_basic, instagram_manage_insights, pages_show_list.
"""

from ._mock import MockEngine, MockPlatformParams

PARAMS = MockPlatformParams(
    follower_range=(8_000, 900_000),
    reach_ratio_range=(0.20, 0.60),
    viral_sigma=0.45,
    er_benchmark=0.012,
    er_mult_range=(0.5, 2.2),
    cadence_range=(1.5, 5.0),
    content_types=[("image", 0.35), ("carousel", 0.25), ("reel", 0.40)],
    engagement_split={"likes": 0.86, "comments": 0.06, "shares": 0.03, "saves": 0.05},
    watch_duration_range=None,  # reels watch time exists in schema; scored from v0.2
    video_types={"reel"},
)


class MockInstagramConnector(MockEngine):
    def __init__(self):
        super().__init__("instagram", PARAMS)
