import pytest
from fastapi.testclient import TestClient

from trashtag.pipeline import db
from trashtag.pipeline.models import (
    IssueClass,
    RawDetection,
    Report,
    Severity,
    new_id,
    now_iso,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "t.db"))

    # Reload constants to pick up new env vars
    import sys

    if "trashtag.constants.filepaths" in sys.modules:
        del sys.modules["trashtag.constants.filepaths"]
    if "trashtag.pipeline.store" in sys.modules:
        del sys.modules["trashtag.pipeline.store"]

    from trashtag.pipeline.store import FilesystemMediaStore

    media_store = FilesystemMediaStore(tmp_path / "media")
    media_store.save(b"JPEGBYTES", "rpt_1_p.jpg")

    conn = db.get_conn(str(tmp_path / "t.db"))
    db.init_db(conn)
    db.insert_report(
        conn,
        Report(
            id="rpt_1",
            media_path="rpt_1_p.jpg",
            lat=18.52,
            lng=73.85,
            captured_at=now_iso(),
        ),
    )
    det = RawDetection(
        id=new_id("det"),
        report_id="rpt_1",
        cls=IssueClass.POTHOLE,
        confidence=0.9,
        lat=18.52,
        lng=73.85,
        captured_at=now_iso(),
        severity=Severity.MEDIUM,
    )
    db.insert_raw_detection(conn, det)
    issue_id = db.create_issue_from(conn, det)

    # A second issue whose evidence row exists but whose media file was never saved,
    # to exercise the FileNotFoundError -> 404 path.
    db.insert_report(
        conn,
        Report(
            id="rpt_2",
            media_path="rpt_2_gone.jpg",
            lat=18.52,
            lng=73.85,
            captured_at=now_iso(),
        ),
    )
    det2 = RawDetection(
        id=new_id("det"),
        report_id="rpt_2",
        cls=IssueClass.POTHOLE,
        confidence=0.9,
        lat=18.52,
        lng=73.85,
        captured_at=now_iso(),
        severity=Severity.MEDIUM,
    )
    db.insert_raw_detection(conn, det2)
    gone_issue_id = db.create_issue_from(conn, det2)
    conn.close()

    # Reload serve to pick up reloaded constants
    if "trashtag.app.serve" in sys.modules:
        del sys.modules["trashtag.app.serve"]

    from trashtag.app.serve import app

    return TestClient(app), issue_id, gone_issue_id


def test_evidence_returns_image(client):
    client_obj, issue_id, _ = client
    r = client_obj.get(f"/v1/issues/{issue_id}/evidence")
    assert r.status_code == 200
    assert r.content == b"JPEGBYTES"


def test_evidence_missing_404(client):
    client_obj, _, _ = client
    assert client_obj.get("/v1/issues/iss_nope/evidence").status_code == 404


def test_evidence_file_gone_404(client):
    client_obj, _, gone_issue_id = client
    # Media row exists but the file on disk does not -> 404, not a 500.
    assert client_obj.get(f"/v1/issues/{gone_issue_id}/evidence").status_code == 404
