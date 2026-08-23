"""Tests for the ingestion endpoint (§2.1)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trashtag.pipeline.db import get_conn, init_db


@pytest.fixture
def tmp_env(tmp_path, monkeypatch):
    """Isolate tests with a temp DB and media dir."""
    monkeypatch.setenv("TRASHTAG_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("TRASHTAG_DB", str(tmp_path / "test.db"))
    return tmp_path


@pytest.fixture
def client(tmp_env):
    """TestClient against a tiny app with the ingest router."""
    # Import AFTER env is set so constants pick up the temp paths.
    from trashtag.pipeline.ingest import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_valid_submission(client, tmp_env):
    """Valid multipart POST → 202, media written, report + queue row."""
    resp = client.post(
        "/v1/reports",
        data={"lat": 18.52, "lng": 73.85},
        files={"media": ("test.jpg", b"fake-image-data", "image/jpeg")},
    )
    body = resp.json()
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {body}"
    assert body["status"] == "queued"
    report_id = body["report_id"]
    assert report_id.startswith("rpt_")

    # Media file exists.
    media_dir = tmp_env / "media"
    assert media_dir.exists()
    assert any(f.name.startswith(report_id) for f in media_dir.iterdir())

    # DB rows exist.
    conn = get_conn(tmp_env / "test.db")
    init_db(conn)
    report_row = conn.execute(
        "SELECT * FROM reports WHERE id = ?", (report_id,)
    ).fetchone()
    assert report_row is not None
    assert report_row["lat"] == 18.52
    queue_row = conn.execute(
        "SELECT * FROM report_queue WHERE report_id = ?", (report_id,)
    ).fetchone()
    assert queue_row is not None
    assert queue_row["status"] == "pending"


def test_duplicate_submission(client):
    """Same media+coords → 200 duplicate, no second row."""
    data = {"lat": 18.52, "lng": 73.85}
    files = {"media": ("dup.jpg", b"same-bytes", "image/jpeg")}

    resp1 = client.post("/v1/reports", data=data, files=files)
    assert resp1.status_code == 202
    id1 = resp1.json()["report_id"]

    resp2 = client.post("/v1/reports", data=data, files=files)
    assert resp2.status_code == 200
    body2 = resp2.json()
    assert body2["status"] == "duplicate"
    assert body2["report_id"] == id1


def test_invalid_lat(client):
    """Out-of-range lat → 422."""
    resp = client.post(
        "/v1/reports",
        data={"lat": 91, "lng": 73.85},
        files={"media": ("x.jpg", b"x", "image/jpeg")},
    )
    assert resp.status_code == 422


def test_bad_device_meta_json(client):
    """Malformed device_meta → 422."""
    resp = client.post(
        "/v1/reports",
        data={"lat": 18.52, "lng": 73.85, "device_meta": "not-json"},
        files={"media": ("x.jpg", b"x", "image/jpeg")},
    )
    assert resp.status_code == 422
