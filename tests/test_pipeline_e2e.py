"""End-to-end: a report POSTed over HTTP (§2.1) flows through processing (§2.2) and
geo-dedup (§2.3) into a single clustered issue.

Uses a fixed detector rather than the stub so the assertion is deterministic — the stub's
per-media randomness is exercised in test_process.py; here we care about the wiring across
all three stages, not what the model "sees".
"""

import pytest
from fastapi.testclient import TestClient

from trashtag.pipeline import db
from trashtag.pipeline.models import IssueClass, RawDetection, Severity, new_id
from trashtag.pipeline.process import run_once
from trashtag.pipeline.store import FilesystemMediaStore


class _FixedDetector:
    """Always reports one pothole at the report's own coordinates."""

    def detect(self, media, lat, lng, captured_at, report_id):
        return [
            RawDetection(
                id=new_id("det"),
                report_id=report_id,
                cls=IssueClass.POTHOLE,
                confidence=0.9,
                lat=lat,
                lng=lng,
                captured_at=captured_at,
                severity=Severity.MEDIUM,
            )
        ]


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Point the pipeline's DB + media at a tmp dir so the test never touches real data/."""
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "e2e.db"))
    return tmp_path


def test_report_flows_to_a_clustered_issue(isolated_env):
    from trashtag.app.serve import app

    client = TestClient(app)

    # Two reports ~5m apart (0.000045° ≈ 5m), distinct media so idempotency keeps them separate.
    base_lat, base_lng = 18.5204, 73.8567
    for i, (blob, dlat) in enumerate([(b"pothole-a", 0.0), (b"pothole-b", 0.000045)]):
        resp = client.post(
            "/v1/reports",
            files={"media": (f"p{i}.jpg", blob, "image/jpeg")},
            data={
                "lat": str(base_lat + dlat),
                "lng": str(base_lng),
                "captured_at": "2026-08-23T07:42:00",
            },
        )
        assert resp.status_code == 202, resp.text
        assert resp.json()["status"] == "queued"

    # §2.2: process everything queued, with the deterministic detector.
    conn = db.get_conn(isolated_env / "e2e.db")
    store = FilesystemMediaStore(isolated_env / "media")
    detector = _FixedDetector()
    assert run_once(conn, store, detector) is not None
    assert run_once(conn, store, detector) is not None
    assert run_once(conn, store, detector) is None  # queue drained

    # Two detections landed, both unclustered.
    assert len(db.unclustered_detections(conn)) == 2

    # §2.3: cluster — the two nearby same-class detections collapse into ONE issue.
    from trashtag.pipeline.dedup import cluster_pending

    assert cluster_pending(conn) == 2
    issues = db.list_issues(conn)
    assert len(issues) == 1
    assert issues[0]["class"] == "pothole"
    assert issues[0]["evidence_count"] == 2
    assert db.unclustered_detections(conn) == []


def test_duplicate_report_is_idempotent(isolated_env):
    from trashtag.app.serve import app

    client = TestClient(app)
    payload = {
        "files": {"media": ("dup.jpg", b"identical-bytes", "image/jpeg")},
        "data": {"lat": "18.52", "lng": "73.85", "captured_at": "2026-08-23T07:42:00"},
    }
    first = client.post("/v1/reports", **payload)
    second = client.post("/v1/reports", **payload)

    assert first.status_code == 202
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"
    assert first.json()["report_id"] == second.json()["report_id"]
