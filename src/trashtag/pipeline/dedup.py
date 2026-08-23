"""Geospatial deduplication / clustering (§2.3): fold raw detections into issues.

Replaces the PostGIS `ST_DWithin` clustering approach (see architecture §2.3) with a haversine-
based scan. RESOLVED/REJECTED issues are excluded from merge candidates (they're not in
OPEN_STATUSES), so a recurrence near a resolved issue correctly opens a new one.
"""

import sqlite3

from trashtag.pipeline.db import (
    attach_evidence,
    create_issue_from,
    mark_clustered,
    open_issues_of_class,
    unclustered_detections,
)
from trashtag.pipeline.geo import haversine

# Minimum gap between two distinct issues. Detections within this radius of an open
# same-class issue are merged as evidence; distinct issues are >=10m apart (product decision).
CLUSTER_RADIUS_M = 10.0


def cluster_pending(
    conn: sqlite3.Connection, radius_m: float = CLUSTER_RADIUS_M
) -> int:
    """Process every unclustered detection: merge into the nearest open issue of the same class
    within `radius_m`, or create a new issue. Returns the number of detections processed."""
    detections = unclustered_detections(conn)
    for det in detections:
        candidates = open_issues_of_class(conn, det.cls)
        nearest, min_dist = None, float("inf")
        for issue in candidates:
            dist = haversine(det.lat, det.lng, issue.lat, issue.lng)
            if dist <= radius_m and dist < min_dist:
                nearest, min_dist = issue, dist
        if nearest:
            attach_evidence(conn, nearest.id, det)
        else:
            create_issue_from(conn, det)
        mark_clustered(conn, det.id)
    return len(detections)
