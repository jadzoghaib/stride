"""Deterministic mock data engine.

Everything derives from seeded RNGs keyed on (platform, handle, purpose), so:
  - the same account always produces the same history (re-seeding is stable),
  - re-syncing on a later day extends the same curves instead of rewriting them,
  - post metrics saturate with post age (a re-sync updates recent posts' numbers),
which makes the ingestion pipeline's idempotency actually observable.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta, timezone

from .base import DemographicSlice, PostData, PostMetricData, SnapshotData

EPOCH = date(2026, 1, 1)  # fixed anchor: follower curves are functions of days-since-epoch
HISTORY_DAYS = 120

AGE_BUCKETS = ["13-17", "18-24", "25-34", "35-44", "45-54", "55+"]
COUNTRY_POOL = [
    ("US", 0.28), ("IN", 0.12), ("GB", 0.09), ("BR", 0.08), ("DE", 0.07),
    ("FR", 0.06), ("CA", 0.05), ("ES", 0.05), ("MX", 0.05), ("AU", 0.04),
]

TITLE_BANK = [
    "Behind the scenes", "Q&A with you all", "Full tutorial", "Day in the life",
    "Collab announcement", "30-day challenge, week %d", "Honest review",
    "What I learned this month", "Setup tour", "Answering your comments",
    "Before and after", "The one mistake to avoid", "Live recap", "Top 5 picks",
]


class MockPlatformParams:
    def __init__(
        self,
        follower_range: tuple[int, int],
        reach_ratio_range: tuple[float, float],
        viral_sigma: float,
        er_benchmark: float,
        er_mult_range: tuple[float, float],
        cadence_range: tuple[float, float],
        content_types: list[tuple[str, float]],
        engagement_split: dict[str, float],
        watch_duration_range: tuple[float, float] | None,
        video_types: set[str],
    ):
        self.follower_range = follower_range
        self.reach_ratio_range = reach_ratio_range
        self.viral_sigma = viral_sigma
        self.er_benchmark = er_benchmark
        self.er_mult_range = er_mult_range
        self.cadence_range = cadence_range
        self.content_types = content_types
        self.engagement_split = engagement_split
        self.watch_duration_range = watch_duration_range
        self.video_types = video_types


class MockEngine:
    """One instance per (platform params, platform name); all methods are pure
    functions of the handle and today's date."""

    def __init__(self, platform: str, params: MockPlatformParams):
        self.platform = platform
        self.params = params

    # -- profile ------------------------------------------------------------

    def _profile(self, handle: str) -> dict:
        rng = random.Random(f"{self.platform}:{handle}:profile")
        lo, hi = self.params.follower_range
        base = math.exp(rng.uniform(math.log(lo), math.log(hi)))
        return {
            "base_followers": base,
            "monthly_growth": rng.triangular(-0.01, 0.10, 0.03),
            "er_mult": rng.uniform(*self.params.er_mult_range),
            "cadence_per_week": rng.uniform(*self.params.cadence_range),
            "reach_ratio": rng.uniform(*self.params.reach_ratio_range),
        }

    def _followers_on(self, handle: str, day: date, prof: dict) -> int:
        months = (day - EPOCH).days / 30.0
        smooth = prof["base_followers"] * (1 + prof["monthly_growth"]) ** months
        noise = random.Random(f"{self.platform}:{handle}:f:{day.isoformat()}").uniform(-0.004, 0.004)
        return max(10, int(smooth * (1 + noise)))

    # -- connector surface ---------------------------------------------------

    def fetch_account_snapshots(self, handle: str) -> list[SnapshotData]:
        prof = self._profile(handle)
        today = date.today()
        out = []
        for offset in range(HISTORY_DAYS - 1, -1, -1):
            day = today - timedelta(days=offset)
            followers = self._followers_on(handle, day, prof)
            pv = random.Random(f"{self.platform}:{handle}:pv:{day}").uniform(0.01, 0.04)
            out.append(SnapshotData(day.isoformat(), followers, int(followers * pv)))
        return out

    def fetch_posts(self, handle: str) -> list[PostData]:
        prof = self._profile(handle)
        rng = random.Random(f"{self.platform}:{handle}:schedule")
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(days=HISTORY_DAYS)
        mean_gap = 7.0 / prof["cadence_per_week"]

        posts: list[PostData] = []
        t = datetime(EPOCH.year, EPOCH.month, EPOCH.day, tzinfo=timezone.utc) - timedelta(days=45)
        i = 0
        while t <= now:
            gap = max(0.25, rng.gauss(mean_gap, mean_gap * 0.4))
            ctype = self._pick_type(rng)
            title = rng.choice(TITLE_BANK)
            if "%d" in title:
                title = title % rng.randint(1, 4)
            t = t + timedelta(days=gap)
            i += 1
            if t < window_start or t > now:
                continue
            external_id = f"{self.platform[:2]}-{handle}-{i:04d}"
            posts.append(
                PostData(
                    external_id=external_id,
                    content_type=ctype,
                    title=title,
                    published_at=t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    permalink=f"https://{self.platform}.example/{handle}/{external_id}",
                    metrics=self._metrics_for(handle, external_id, t, now, prof),
                )
            )
        return posts

    def _pick_type(self, rng: random.Random) -> str:
        r = rng.random()
        acc = 0.0
        for name, w in self.params.content_types:
            acc += w
            if r <= acc:
                return name
        return self.params.content_types[-1][0]

    def _metrics_for(
        self, handle: str, external_id: str, published: datetime, captured: datetime, prof: dict
    ) -> PostMetricData:
        p = self.params
        rng = random.Random(f"{self.platform}:{external_id}:metrics")
        followers = self._followers_on(handle, published.date(), prof)

        final_reach = followers * prof["reach_ratio"] * rng.lognormvariate(0, p.viral_sigma)
        er = p.er_benchmark * prof["er_mult"] * rng.lognormvariate(0, 0.35)

        # engagement counts saturate over the first ~week after publishing
        age_days = max(0.05, (captured - published).total_seconds() / 86400)
        maturity = 1 - math.exp(-age_days / 3.0)

        reach = int(final_reach * maturity)
        impressions = int(reach * rng.uniform(1.15, 1.7))
        engagement_total = reach * er
        counts = {}
        for kind, share in p.engagement_split.items():
            counts[kind] = int(engagement_total * share * rng.uniform(0.85, 1.15))

        watch_time_s = avg_dur = None
        if p.watch_duration_range is not None:
            lo, hi = p.watch_duration_range
            avg_dur = round(rng.uniform(lo, hi) * min(prof["er_mult"], 1.6), 1)
            watch_time_s = int(impressions * avg_dur)

        return PostMetricData(
            reach=reach,
            impressions=impressions,
            likes=counts.get("likes", 0),
            comments=counts.get("comments", 0),
            shares=counts.get("shares", 0),
            saves=counts.get("saves", 0),
            watch_time_s=watch_time_s,
            avg_view_duration_s=avg_dur,
        )

    def fetch_demographics(self, handle: str) -> list[DemographicSlice]:
        rng = random.Random(f"{self.platform}:{handle}:demo")
        out: list[DemographicSlice] = []

        # age: a peak bucket with decay on both sides
        peak = rng.choice([1, 1, 2, 2, 3])  # mostly 18-24 / 25-34, sometimes 35-44
        weights = [math.exp(-abs(i - peak) / rng.uniform(0.8, 1.6)) for i in range(len(AGE_BUCKETS))]
        total = sum(weights)
        for bucket, w in zip(AGE_BUCKETS, weights):
            out.append(DemographicSlice("age", bucket, round(w / total, 4)))

        female = rng.uniform(0.25, 0.75)
        other = rng.uniform(0.01, 0.05)
        out.append(DemographicSlice("gender", "female", round(female, 4)))
        out.append(DemographicSlice("gender", "male", round(1 - female - other, 4)))
        out.append(DemographicSlice("gender", "other", round(other, 4)))

        picked = rng.sample(COUNTRY_POOL, 6)
        cw = [(c, base * rng.uniform(0.5, 2.0)) for c, base in picked]
        ctotal = sum(w for _, w in cw) / rng.uniform(0.75, 0.9)  # leave a remainder for OTHER
        acc = 0.0
        for c, w in sorted(cw, key=lambda x: -x[1]):
            share = round(w / ctotal, 4)
            acc += share
            out.append(DemographicSlice("country", c, share))
        out.append(DemographicSlice("country", "OTHER", round(max(0.0, 1 - acc), 4)))
        return out
