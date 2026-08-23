"""Tests for the geo-dedup clustering stage (§2.3)."""

import sqlite3

from trashtag.pipeline.db import (
    get_conn,
    get_issue,
    init_db,
    insert_raw_detection,
    insert_report,
    list_issues,
    set_issue_status,
    unclustered_detections,
)
from trashtag.pipeline.dedup import cluster_pending
from trashtag.pipeline.models import (
    IssueClass,
    IssueStatus,
    RawDetection,
    Report,
    Severity,
    new_id,
)


def _make_report(conn: sqlite3.Connection, report_id: str) -> None:
    """Insert a minimal report to satisfy foreign key constraints."""
    insert_report(
        conn,
        Report(
            id=report_id,
            media_path="test.jpg",
            lat=18.52,
            lng=73.85,
            captured_at="2026-08-23T00:00:00",
        ),
    )


def test_nearby_same_class_clusters_into_one_issue():
    """Two detections of the same class ~5m apart → one issue with evidence_count 2."""
    conn = get_conn(":memory:")
    init_db(conn)
    # Base point in Pune
    lat, lng = 18.52, 73.85
    rpt1, rpt2 = new_id("rpt"), new_id("rpt")
    _make_report(conn, rpt1)
    _make_report(conn, rpt2)
    det1 = RawDetection(
        id=new_id("det"),
        report_id=rpt1,
        cls=IssueClass.POTHOLE,
        confidence=0.8,
        lat=lat,
        lng=lng,
        captured_at="2026-08-23T07:00:00",
        severity=Severity.MEDIUM,
    )
    det2 = RawDetection(
        id=new_id("det"),
        report_id=rpt2,
        cls=IssueClass.POTHOLE,
        confidence=0.9,
        lat=lat + 0.000045,  # ~5m north
        lng=lng,
        captured_at="2026-08-23T07:05:00",
        severity=Severity.HIGH,
    )
    insert_raw_detection(conn, det1)
    insert_raw_detection(conn, det2)
    count = cluster_pending(conn)
    assert count == 2
    issues = list_issues(conn)
    assert len(issues) == 1
    assert issues[0]["evidence_count"] == 2
    assert issues[0]["confidence"] == 0.9  # max of the two
    assert unclustered_detections(conn) == []


def test_distant_same_class_creates_separate_issues():
    """Two detections of the same class ~50m apart → two separate issues."""
    conn = get_conn(":memory:")
    init_db(conn)
    lat, lng = 18.52, 73.85
    rpt1, rpt2 = new_id("rpt"), new_id("rpt")
    _make_report(conn, rpt1)
    _make_report(conn, rpt2)
    det1 = RawDetection(
        id=new_id("det"),
        report_id=rpt1,
        cls=IssueClass.GARBAGE,
        confidence=0.7,
        lat=lat,
        lng=lng,
        captured_at="2026-08-23T08:00:00",
        severity=Severity.MEDIUM,
    )
    det2 = RawDetection(
        id=new_id("det"),
        report_id=rpt2,
        cls=IssueClass.GARBAGE,
        confidence=0.8,
        lat=lat + 0.00045,  # ~50m north
        lng=lng,
        captured_at="2026-08-23T08:10:00",
        severity=Severity.MEDIUM,
    )
    insert_raw_detection(conn, det1)
    insert_raw_detection(conn, det2)
    count = cluster_pending(conn)
    assert count == 2
    issues = list_issues(conn)
    assert len(issues) == 2
    for issue in issues:
        assert issue["evidence_count"] == 1


def test_same_location_different_class_creates_separate_issues():
    """Two detections at the same spot but different class → two issues."""
    conn = get_conn(":memory:")
    init_db(conn)
    lat, lng = 18.52, 73.85
    rpt1, rpt2 = new_id("rpt"), new_id("rpt")
    _make_report(conn, rpt1)
    _make_report(conn, rpt2)
    det1 = RawDetection(
        id=new_id("det"),
        report_id=rpt1,
        cls=IssueClass.POTHOLE,
        confidence=0.8,
        lat=lat,
        lng=lng,
        captured_at="2026-08-23T09:00:00",
        severity=Severity.MEDIUM,
    )
    det2 = RawDetection(
        id=new_id("det"),
        report_id=rpt2,
        cls=IssueClass.GARBAGE,
        confidence=0.8,
        lat=lat,
        lng=lng,
        captured_at="2026-08-23T09:05:00",
        severity=Severity.MEDIUM,
    )
    insert_raw_detection(conn, det1)
    insert_raw_detection(conn, det2)
    count = cluster_pending(conn)
    assert count == 2
    issues = list_issues(conn)
    assert len(issues) == 2
    classes = {issue["class"] for issue in issues}
    assert classes == {"pothole", "garbage"}


def test_near_resolved_issue_creates_new_issue():
    """A detection ~5m from a RESOLVED issue → opens a new issue (recurrence)."""
    conn = get_conn(":memory:")
    init_db(conn)
    lat, lng = 18.52, 73.85
    # First detection creates an issue
    rpt1 = new_id("rpt")
    _make_report(conn, rpt1)
    det1 = RawDetection(
        id=new_id("det"),
        report_id=rpt1,
        cls=IssueClass.POTHOLE,
        confidence=0.8,
        lat=lat,
        lng=lng,
        captured_at="2026-08-20T10:00:00",
        severity=Severity.MEDIUM,
    )
    insert_raw_detection(conn, det1)
    cluster_pending(conn)
    issues = list_issues(conn)
    assert len(issues) == 1
    issue_id = issues[0]["id"]
    # Mark it resolved
    set_issue_status(conn, issue_id, IssueStatus.RESOLVED)
    # Second detection nearby
    rpt2 = new_id("rpt")
    _make_report(conn, rpt2)
    det2 = RawDetection(
        id=new_id("det"),
        report_id=rpt2,
        cls=IssueClass.POTHOLE,
        confidence=0.9,
        lat=lat + 0.000045,  # ~5m north
        lng=lng,
        captured_at="2026-08-23T10:00:00",
        severity=Severity.MEDIUM,
    )
    insert_raw_detection(conn, det2)
    count = cluster_pending(conn)
    assert count == 1
    issues = list_issues(conn)
    assert len(issues) == 2
    # One resolved, one new
    statuses = {issue["status"] for issue in issues}
    assert statuses == {"resolved", "new"}
    new_issue = next(i for i in issues if i["status"] == "new")
    assert new_issue["evidence_count"] == 1


def test_chooses_nearest_when_multiple_candidates():
    """When multiple open issues are within radius, attach to the nearest one."""
    conn = get_conn(":memory:")
    init_db(conn)
    lat, lng = 18.52, 73.85
    # Two initial detections 20m apart (outside cluster radius)
    rpt1, rpt2 = new_id("rpt"), new_id("rpt")
    _make_report(conn, rpt1)
    _make_report(conn, rpt2)
    det1 = RawDetection(
        id=new_id("det"),
        report_id=rpt1,
        cls=IssueClass.POTHOLE,
        confidence=0.8,
        lat=lat,
        lng=lng,
        captured_at="2026-08-23T11:00:00",
        severity=Severity.MEDIUM,
    )
    det2 = RawDetection(
        id=new_id("det"),
        report_id=rpt2,
        cls=IssueClass.POTHOLE,
        confidence=0.8,
        lat=lat + 0.00018,  # ~20m north
        lng=lng,
        captured_at="2026-08-23T11:05:00",
        severity=Severity.MEDIUM,
    )
    insert_raw_detection(conn, det1)
    insert_raw_detection(conn, det2)
    cluster_pending(conn)
    issues = list_issues(conn)
    assert len(issues) == 2  # 20m apart, each creates its own issue
    # Third detection 7m north of first (so 13m south of second) - within range of both
    rpt3 = new_id("rpt")
    _make_report(conn, rpt3)
    det3 = RawDetection(
        id=new_id("det"),
        report_id=rpt3,
        cls=IssueClass.POTHOLE,
        confidence=0.9,
        lat=lat + 0.000063,  # ~7m north of first, ~13m south of second
        lng=lng,
        captured_at="2026-08-23T11:10:00",
        severity=Severity.MEDIUM,
    )
    insert_raw_detection(conn, det3)
    cluster_pending(conn)
    issues = list_issues(conn)
    assert len(issues) == 2  # still two issues
    # The issue near the first detection should have evidence_count 2 (det1 + det3)
    issue1 = get_issue(conn, issues[0]["id"])
    issue2 = get_issue(conn, issues[1]["id"])
    counts = sorted([issue1["evidence_count"], issue2["evidence_count"]])
    assert counts == [1, 2]
    # Verify det3 attached to the NEARER issue (~7m from first, ~13m from second)
    merged_issue = issue1 if issue1["evidence_count"] == 2 else issue2
    # The merged issue's coords should be nearer to det3 than the other issue
    assert abs(merged_issue["lat"] - det3.lat) < 0.0001  # within ~11m of det3
