"""Connector interface — the seam between CreatorLens and each platform.

Mock connectors implement this today; live connectors implement the same three
methods against the real endpoints (docs/real-api-mapping.md) and nothing
downstream changes. A connector receives a ready, authenticated client in the
live case — never raw secrets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PostMetricData:
    reach: int
    impressions: int
    likes: int
    comments: int
    shares: int
    saves: int = 0
    watch_time_s: int | None = None
    avg_view_duration_s: float | None = None


@dataclass
class PostData:
    external_id: str
    content_type: str
    title: str
    published_at: str  # ISO UTC
    permalink: str
    metrics: PostMetricData = field(default=None)  # current values at fetch time


@dataclass
class SnapshotData:
    snapshot_date: str  # YYYY-MM-DD
    followers: int
    profile_views: int


@dataclass
class DemographicSlice:
    dimension: str  # age | gender | country
    bucket: str
    share: float


class PlatformConnector(Protocol):
    platform: str

    def fetch_account_snapshots(self, handle: str) -> list[SnapshotData]: ...

    def fetch_posts(self, handle: str) -> list[PostData]: ...

    def fetch_demographics(self, handle: str) -> list[DemographicSlice]: ...


def get_connector(platform: str, source: str = "mock") -> PlatformConnector:
    if source != "mock":
        raise NotImplementedError(
            f"live connector for {platform} not implemented — see docs/real-api-mapping.md"
        )
    from .instagram import MockInstagramConnector
    from .tiktok import MockTikTokConnector
    from .youtube import MockYouTubeConnector

    registry = {
        "instagram": MockInstagramConnector,
        "youtube": MockYouTubeConnector,
        "tiktok": MockTikTokConnector,
    }
    try:
        return registry[platform]()
    except KeyError:
        raise ValueError(f"unknown platform: {platform}") from None
