import pytest

from trashtag.pipeline import db
from trashtag.pipeline.models import (
    IssueClass,
    IssueStatus,
    RawDetection,
    Report,
    Severity,
    can_transition,
    new_id,
    now_iso,
)


@pytest.fixture
def conn():
    c = db.get_conn(":memory:")
    db.init_db(c)
    return c


def test_can_transition():
    assert can_transition(IssueStatus.NEW, IssueStatus.VERIFIED)
    assert can_transition(IssueStatus.NEW, IssueStatus.REJECTED)
    assert not can_transition(IssueStatus.RESOLVED, IssueStatus.NEW)
    assert not can_transition(IssueStatus.REJECTED, IssueStatus.VERIFIED)


def _seed_one_issue(conn):
    det = RawDetection(id=new_id("det"), report_id="rpt_x", cls=IssueClass.POTHOLE,
                       confidence=0.9, lat=18.52, lng=73.85, captured_at=now_iso(),
                       severity=Severity.MEDIUM)
    # a report row is needed for the FK on raw_detections/evidence
    db.insert_report(conn, Report(id="rpt_x", media_path="rpt_x_p.jpg", lat=18.52, lng=73.85, captured_at=now_iso()))
    db.insert_raw_detection(conn, det)
    return db.create_issue_from(conn, det), det


def test_update_issue_legal_and_illegal(conn):
    issue_id, _ = _seed_one_issue(conn)
    updated = db.update_issue(conn, issue_id, status="verified")
    assert updated["status"] == "verified"
    db.update_issue(conn, issue_id, severity="high", note="confirmed on site")
    assert db.get_issue(conn, issue_id)["severity"] == "high"
    with pytest.raises(ValueError):
        db.update_issue(conn, issue_id, status="new")  # verified -> new illegal


def test_update_issue_missing(conn):
    with pytest.raises(KeyError):
        db.update_issue(conn, "iss_nope", status="verified")


def test_issue_evidence_media(conn):
    issue_id, _ = _seed_one_issue(conn)
    assert db.issue_evidence_media(conn, issue_id) == "rpt_x_p.jpg"
    assert db.issue_evidence_media(conn, "iss_nope") is None


def test_seed_issues_idempotent(conn):
    rows = [{"id": "iss_seed1", "class": "pothole", "status": "new", "lat": 18.5, "lng": 73.8,
             "confidence": 0.8, "severity": "medium", "first_seen": now_iso(), "last_seen": now_iso(),
             "evidence_count": 1}]
    assert db.seed_issues(conn, rows) == 1
    assert db.seed_issues(conn, rows) == 0  # idempotent
    assert len(db.list_issues(conn)) == 1
