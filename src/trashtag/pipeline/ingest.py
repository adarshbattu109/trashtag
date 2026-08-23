"""Ingestion endpoint (§2.1): multipart upload → idempotency check → queue."""

import contextlib
import json
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Response, UploadFile, status

from trashtag.constants.filepaths import DB_PATH
from trashtag.pipeline.db import (
    enqueue,
    get_conn,
    init_db,
    insert_report,
    report_id_for_idempotency,
)
from trashtag.pipeline.geo import idempotency_key
from trashtag.pipeline.models import Report, new_id, now_iso
from trashtag.pipeline.store import FilesystemMediaStore

router = APIRouter()

_db_initialized = set()


def _conn():
    """Connection helper — opens a DB connection. Respects TRASHTAG_DB env for tests."""
    # ponytail: check env each call so tests can override without reloading modules; single-
    # process sync handler closes conn after each request, no pooling (move to a pool on scale)
    db_path = os.getenv("TRASHTAG_DB") or str(DB_PATH)
    conn = get_conn(db_path)
    if db_path not in _db_initialized:
        init_db(conn)
        _db_initialized.add(db_path)
    return conn


def _store():
    """Store helper — created per-request so tests can override paths via env."""
    data_dir = os.getenv("TRASHTAG_DATA_DIR")
    return FilesystemMediaStore(Path(data_dir) / "media" if data_dir else None)


@router.post(
    "/v1/reports", operation_id="submit_report", status_code=status.HTTP_202_ACCEPTED
)
def submit_report(
    response: Response,
    media: UploadFile,
    lat: float = Form(...),
    lng: float = Form(...),
    captured_at: str = Form(default=""),
    source: str = Form(default="upload"),
    user_id: str | None = Form(default=None),
    device_meta: str = Form(default="{}"),
):
    """Submit a report: photo + location. Idempotent (duplicate detection via content hash)."""
    if not (-90 <= lat <= 90):
        raise HTTPException(422, "lat must be in [-90, 90]")
    if not (-180 <= lng <= 180):
        raise HTTPException(422, "lng must be in [-180, 180]")
    if captured_at:
        try:
            datetime.fromisoformat(captured_at)
        except ValueError:
            raise HTTPException(422, "captured_at must be an ISO-8601 timestamp")

    media_bytes = media.file.read()
    if not media_bytes:
        raise HTTPException(422, "media file is empty")

    try:
        device_dict = json.loads(device_meta)
    except json.JSONDecodeError:
        raise HTTPException(422, "device_meta must be valid JSON")

    ts = captured_at or now_iso()
    idem_key = idempotency_key(media_bytes, lat, lng)

    with contextlib.closing(_conn()) as conn:
        existing = report_id_for_idempotency(conn, idem_key)
        if existing:
            response.status_code = status.HTTP_200_OK
            return {"report_id": existing, "status": "duplicate"}

        report_id = new_id("rpt")
        media_path = _store().save(media_bytes, f"{report_id}_{media.filename}")
        report = Report(
            id=report_id,
            media_path=media_path,
            lat=lat,
            lng=lng,
            captured_at=ts,
            source=source,
            user_id=user_id,
            device_meta=device_dict,
            idempotency_key=idem_key,
        )
        insert_report(conn, report)
        enqueue(conn, report_id)
        return {"report_id": report_id, "status": "queued"}
