"""Tests for the processing stage (§2.2)."""

import sqlite3
from pathlib import Path

import pytest

from trashtag.pipeline.db import (
    enqueue,
    get_conn,
    init_db,
    insert_report,
    unclustered_detections,
)
from trashtag.pipeline.detector import StubDetector
from trashtag.pipeline.models import Report, now_iso
from trashtag.pipeline.process import CONFIDENCE_THRESHOLD, process_one, run_once
from trashtag.pipeline.store import FilesystemMediaStore


@pytest.fixture
def conn() -> sqlite3.Connection:
    """In-memory DB with schema."""
    c = get_conn(":memory:")
    init_db(c)
    return c


@pytest.fixture
def store(tmp_path: Path) -> FilesystemMediaStore:
    """Temp filesystem store."""
    return FilesystemMediaStore(tmp_path)


def test_stub_detector_determinism():
    """StubDetector returns identical detections for the same media bytes."""
    detector = StubDetector()
    media = b"test image data"
    lat, lng = 18.52, 73.85
    captured = now_iso()
    report_id = "rpt_test"

    det1 = detector.detect(media, lat, lng, captured, report_id)
    det2 = detector.detect(media, lat, lng, captured, report_id)

    assert len(det1) == len(det2)
    for d1, d2 in zip(det1, det2):
        # IDs differ (new_id generates fresh), but everything else matches
        assert d1.cls == d2.cls
        assert d1.confidence == d2.confidence
        assert d1.lat == d2.lat
        assert d1.lng == d2.lng
        assert d1.bbox == d2.bbox
        assert d1.severity == d2.severity


def test_confidence_gate(conn: sqlite3.Connection, store: FilesystemMediaStore):
    """Detections below the confidence threshold are not persisted."""
    # Find media bytes that yield a low-confidence detection
    detector = StubDetector()
    for candidate in range(256):
        media = bytes([candidate] * 32)
        dets = detector.detect(media, 18.52, 73.85, now_iso(), "rpt_x")
        if dets and any(d.confidence < CONFIDENCE_THRESHOLD for d in dets):
            break
    else:
        pytest.skip("Could not find media bytes yielding low-confidence detection")

    # Insert report with that media
    report = Report(
        id="rpt_gate",
        media_path="gate.jpg",
        lat=18.52,
        lng=73.85,
        captured_at=now_iso(),
    )
    store.save(media, report.media_path)
    insert_report(conn, report)
    enqueue(conn, report.id)

    # Process it
    process_one(conn, store, detector, report.id)

    # Only high-confidence detections should be in the DB
    persisted = unclustered_detections(conn)
    assert all(d.confidence >= CONFIDENCE_THRESHOLD for d in persisted)


def test_run_once_end_to_end(conn: sqlite3.Connection, store: FilesystemMediaStore):
    """run_once processes a queued report and persists surviving detections."""
    media = b"another test image"
    report = Report(
        id="rpt_e2e", media_path="e2e.jpg", lat=18.52, lng=73.85, captured_at=now_iso()
    )
    store.save(media, report.media_path)
    insert_report(conn, report)
    enqueue(conn, report.id)

    detector = StubDetector()
    result = run_once(conn, store, detector)

    assert result == report.id
    # Check that raw_detections has entries
    dets = unclustered_detections(conn)
    assert len(dets) > 0
    # Check that queue status is done
    row = conn.execute(
        "SELECT status FROM report_queue WHERE report_id = ?", (report.id,)
    ).fetchone()
    assert row["status"] == "done"


def test_run_once_empty_queue(conn: sqlite3.Connection, store: FilesystemMediaStore):
    """run_once returns None when the queue is empty."""
    detector = StubDetector()
    result = run_once(conn, store, detector)
    assert result is None
