"""Geospatial helpers. The zero-infra substitute for PostGIS distance queries (§2.3).

Haversine is accurate to well under a metre at city scale, which is all the ~10–15m clustering
threshold needs. Swap in PostGIS `ST_DWithin` when the store moves to Postgres.
"""

import hashlib
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_M = 6_371_000.0


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in metres."""
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = (
        sin(d_lat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(d_lng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * asin(sqrt(a))


def idempotency_key(media_bytes: bytes, lat: float, lng: float) -> str:
    """A dedup key for intake (§2.1): identical photo bytes at the same ~11m location is the
    same submission, regardless of upload time. Location is bucketed to ~11m (4 decimal places);
    the media hash keeps distinct photos apart.
    """
    media_hash = hashlib.sha256(media_bytes).hexdigest()
    geo_bucket = f"{lat:.4f},{lng:.4f}"
    raw = f"{media_hash}|{geo_bucket}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


if __name__ == "__main__":
    # Self-check: known distance (Pune FC Road ~ JM Road is roughly 1.3km) and idempotency.
    d = haversine(18.5204, 73.8567, 18.5314, 73.8446)
    assert 1000 < d < 2000, d
    assert haversine(18.52, 73.85, 18.52, 73.85) == 0.0
    k1 = idempotency_key(b"x", 18.5204, 73.8567)
    k2 = idempotency_key(b"x", 18.52041, 73.85669)
    assert k1 == k2, "near-identical location should collide"
    assert k1 != idempotency_key(b"y", 18.5204, 73.8567)
    print(f"ok — {d:.0f}m between the two Pune points, idempotency buckets as designed")
