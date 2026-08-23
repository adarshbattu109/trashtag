"""Background worker: drain the report queue (process → dedup). In-process, cooperative —
the zero-infra stand-in for a Celery/Kafka worker."""

import logging

from trashtag.pipeline import db
from trashtag.pipeline.dedup import cluster_pending
from trashtag.pipeline.process import process_one

logger = logging.getLogger(__name__)


def run_worker_tick(conn, store, detector) -> int:
    """Process every pending report, then cluster new detections. Returns reports processed."""
    processed = 0
    while (report_id := db.dequeue(conn)) is not None:
        try:
            process_one(conn, store, detector, report_id)
            processed += 1
        except Exception:
            logger.exception("worker: failed processing %s", report_id)
            db.set_queue_status(conn, report_id, "failed")
    if processed:
        cluster_pending(conn)
    return processed
