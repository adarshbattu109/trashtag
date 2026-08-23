"""Processing stage (§2.2): detect issues in queued reports, apply confidence gate, persist."""

import sqlite3

from trashtag.pipeline.db import (
    dequeue,
    get_report,
    insert_raw_detection,
    set_queue_status,
)
from trashtag.pipeline.interfaces import Detector
from trashtag.pipeline.models import RawDetection
from trashtag.pipeline.store import FilesystemMediaStore

CONFIDENCE_THRESHOLD = 0.5  # Drop detections below this (§2.2)


def process_one(
    conn: sqlite3.Connection,
    store: FilesystemMediaStore,
    detector: Detector,
    report_id: str,
) -> list[RawDetection]:
    """Process one report: load, detect, filter by confidence, persist survivors."""
    report = get_report(conn, report_id)
    if not report:
        set_queue_status(conn, report_id, "failed")
        return []

    media = store.open(report.media_path)
    detections = detector.detect(
        media, report.lat, report.lng, report.captured_at, report_id
    )

    # Confidence gate: keep only high-confidence detections
    kept = [d for d in detections if d.confidence >= CONFIDENCE_THRESHOLD]

    for det in kept:
        insert_raw_detection(conn, det)

    set_queue_status(conn, report_id, "done")
    return kept


def run_once(
    conn: sqlite3.Connection, store: FilesystemMediaStore, detector: Detector
) -> str | None:
    """Dequeue and process one report. Returns the report_id if work was done, else None."""
    report_id = dequeue(conn)
    if not report_id:
        return None
    process_one(conn, store, detector, report_id)
    return report_id
