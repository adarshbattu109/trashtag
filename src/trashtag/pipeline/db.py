"""SQLite persistence + primitives for the pipeline — the zero-infra stand-in for
PostgreSQL/PostGIS (architecture §2.3). This module owns the schema and every SQL statement;
the stages call these functions and never write SQL themselves, so the schema can't drift.

Tables (§2.3 schema): reports, report_queue, raw_detections (immutable, source-tagged),
issues (deduplicated, lifecycle), issue_evidence (many detections → one issue, audit trail).

Distance/clustering policy is NOT here — it lives in the dedup stage. This module only fetches
candidate rows and applies mutations; `dedup.py` decides what counts as "near".
"""

import json
import sqlite3
from pathlib import Path

from trashtag.constants.filepaths import DB_PATH
from trashtag.pipeline.models import (
    OPEN_STATUSES,
    Issue,
    IssueClass,
    IssueStatus,
    RawDetection,
    Report,
    Severity,
    can_transition,
    new_id,
    now_iso,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id              TEXT PRIMARY KEY,
    media_path      TEXT NOT NULL,
    lat             REAL NOT NULL,
    lng             REAL NOT NULL,
    captured_at     TEXT NOT NULL,
    source          TEXT NOT NULL,
    user_id         TEXT,
    device_meta     TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT UNIQUE,
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS report_queue (
    report_id   TEXT PRIMARY KEY REFERENCES reports(id),
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending | processing | done | failed
    enqueued_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_detections (
    id          TEXT PRIMARY KEY,
    report_id   TEXT NOT NULL REFERENCES reports(id),
    class       TEXT NOT NULL,
    confidence  REAL NOT NULL,
    lat         REAL NOT NULL,
    lng         REAL NOT NULL,
    captured_at TEXT NOT NULL,
    bbox        TEXT,                                -- json [x,y,w,h] or null
    severity    TEXT NOT NULL,
    clustered   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS issues (
    id             TEXT PRIMARY KEY,
    class          TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'new',
    lat            REAL NOT NULL,
    lng            REAL NOT NULL,
    confidence     REAL NOT NULL,
    severity       TEXT NOT NULL,
    first_seen     TEXT NOT NULL,
    last_seen      TEXT NOT NULL,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    note           TEXT
);
CREATE TABLE IF NOT EXISTS issue_evidence (
    id           TEXT PRIMARY KEY,
    issue_id     TEXT NOT NULL REFERENCES issues(id),
    detection_id TEXT NOT NULL REFERENCES raw_detections(id),
    added_at     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS issue_events (
    id        TEXT PRIMARY KEY,
    issue_id  TEXT NOT NULL REFERENCES issues(id),
    event     TEXT NOT NULL,      -- e.g. status:verified | severity:high | note
    detail    TEXT,
    source    TEXT NOT NULL DEFAULT 'ops-dashboard',
    at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_raw_unclustered ON raw_detections(clustered);
CREATE INDEX IF NOT EXISTS idx_issue_class_status ON issues(class, status);
"""


def get_conn(path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Open a connection with row access by name and foreign keys enforced."""
    p = Path(path)
    if p.parent and str(p.parent) not in ("", "."):
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables/indexes if absent. Idempotent."""
    conn.executescript(SCHEMA)
    conn.commit()


# --- row <-> model converters -------------------------------------------------------------


def _report(row: sqlite3.Row) -> Report:
    return Report(
        id=row["id"],
        media_path=row["media_path"],
        lat=row["lat"],
        lng=row["lng"],
        captured_at=row["captured_at"],
        source=row["source"],
        user_id=row["user_id"],
        device_meta=json.loads(row["device_meta"]),
        idempotency_key=row["idempotency_key"],
    )


def _detection(row: sqlite3.Row) -> RawDetection:
    return RawDetection(
        id=row["id"],
        report_id=row["report_id"],
        cls=IssueClass(row["class"]),
        confidence=row["confidence"],
        lat=row["lat"],
        lng=row["lng"],
        captured_at=row["captured_at"],
        bbox=tuple(json.loads(row["bbox"])) if row["bbox"] else None,
        severity=Severity(row["severity"]),
        clustered=bool(row["clustered"]),
    )


def _issue(row: sqlite3.Row) -> Issue:
    return Issue(
        id=row["id"],
        cls=IssueClass(row["class"]),
        status=IssueStatus(row["status"]),
        lat=row["lat"],
        lng=row["lng"],
        confidence=row["confidence"],
        severity=Severity(row["severity"]),
        first_seen=row["first_seen"],
        last_seen=row["last_seen"],
        evidence_count=row["evidence_count"],
    )


# --- reports + queue (§2.1) ----------------------------------------------------------------


def report_id_for_idempotency(conn: sqlite3.Connection, key: str) -> str | None:
    """Return an existing report id for this idempotency key, or None. Lets intake reject a
    duplicate upload without inserting a second row."""
    row = conn.execute(
        "SELECT id FROM reports WHERE idempotency_key = ?", (key,)
    ).fetchone()
    return row["id"] if row else None


def insert_report(conn: sqlite3.Connection, report: Report) -> None:
    """Persist a Report. Assumes the caller already checked idempotency."""
    conn.execute(
        """INSERT INTO reports
           (id, media_path, lat, lng, captured_at, source, user_id, device_meta,
            idempotency_key, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            report.id,
            report.media_path,
            report.lat,
            report.lng,
            report.captured_at,
            report.source,
            report.user_id,
            json.dumps(report.device_meta),
            report.idempotency_key,
            now_iso(),
        ),
    )
    conn.commit()


def get_report(conn: sqlite3.Connection, report_id: str) -> Report | None:
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return _report(row) if row else None


def enqueue(conn: sqlite3.Connection, report_id: str) -> None:
    """Add a report to the processing queue (pending)."""
    conn.execute(
        "INSERT OR REPLACE INTO report_queue (report_id, status, enqueued_at) VALUES (?, 'pending', ?)",
        (report_id, now_iso()),
    )
    conn.commit()


def dequeue(conn: sqlite3.Connection) -> str | None:
    """Claim the oldest pending report (mark it 'processing') and return its id, or None if the
    queue is empty. Single-process prototype — no cross-worker locking (see ponytail note)."""
    # ponytail: SELECT-then-UPDATE is not atomic across processes; fine for the single-process
    # slice. Move to SELECT ... FOR UPDATE SKIP LOCKED on Postgres, or a real broker, for scale.
    row = conn.execute(
        "SELECT report_id FROM report_queue WHERE status = 'pending' ORDER BY enqueued_at LIMIT 1"
    ).fetchone()
    if not row:
        return None
    conn.execute(
        "UPDATE report_queue SET status = 'processing' WHERE report_id = ?",
        (row["report_id"],),
    )
    conn.commit()
    return row["report_id"]


def set_queue_status(conn: sqlite3.Connection, report_id: str, status: str) -> None:
    """Mark a queued report done/failed after processing."""
    conn.execute(
        "UPDATE report_queue SET status = ? WHERE report_id = ?", (status, report_id)
    )
    conn.commit()


# --- raw detections (§2.2 writes, §2.3 reads) ---------------------------------------------


def insert_raw_detection(conn: sqlite3.Connection, det: RawDetection) -> None:
    """Persist one detection (immutable). Written by the processing stage."""
    conn.execute(
        """INSERT INTO raw_detections
           (id, report_id, class, confidence, lat, lng, captured_at, bbox, severity,
            clustered, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            det.id,
            det.report_id,
            str(det.cls),
            det.confidence,
            det.lat,
            det.lng,
            det.captured_at,
            json.dumps(list(det.bbox)) if det.bbox else None,
            str(det.severity),
            int(det.clustered),
            now_iso(),
        ),
    )
    conn.commit()


def unclustered_detections(conn: sqlite3.Connection) -> list[RawDetection]:
    """All detections not yet folded into an issue, oldest first (the dedup work queue)."""
    rows = conn.execute(
        "SELECT * FROM raw_detections WHERE clustered = 0 ORDER BY created_at"
    ).fetchall()
    return [_detection(r) for r in rows]


def mark_clustered(conn: sqlite3.Connection, detection_id: str) -> None:
    conn.execute(
        "UPDATE raw_detections SET clustered = 1 WHERE id = ?", (detection_id,)
    )
    conn.commit()


# --- issues + evidence (§2.3) --------------------------------------------------------------


def open_issues_of_class(conn: sqlite3.Connection, cls: IssueClass) -> list[Issue]:
    """Candidate issues a new detection of this class could merge into: same class, still in an
    OPEN lifecycle status. The dedup stage applies the distance threshold to these."""
    placeholders = ",".join("?" for _ in OPEN_STATUSES)
    rows = conn.execute(
        f"SELECT * FROM issues WHERE class = ? AND status IN ({placeholders})",
        (str(cls), *[str(s) for s in OPEN_STATUSES]),
    ).fetchall()
    return [_issue(r) for r in rows]


def create_issue_from(conn: sqlite3.Connection, det: RawDetection) -> str:
    """Open a new issue seeded from a detection, and record that detection as its first
    evidence. Returns the new issue id."""
    issue_id = new_id("iss")
    ts = det.captured_at
    conn.execute(
        """INSERT INTO issues
           (id, class, status, lat, lng, confidence, severity, first_seen, last_seen,
            evidence_count)
           VALUES (?,?, 'new', ?,?,?,?,?,?, 0)""",
        (
            issue_id,
            str(det.cls),
            det.lat,
            det.lng,
            det.confidence,
            str(det.severity),
            ts,
            ts,
        ),
    )
    conn.commit()
    attach_evidence(conn, issue_id, det)
    return issue_id


def attach_evidence(conn: sqlite3.Connection, issue_id: str, det: RawDetection) -> None:
    """Record `det` as evidence for `issue_id` and roll up the issue's aggregates: bump
    evidence_count, extend last_seen, and raise confidence to the strongest detection seen."""
    conn.execute(
        "INSERT INTO issue_evidence (id, issue_id, detection_id, added_at) VALUES (?,?,?,?)",
        (new_id("ev"), issue_id, det.id, now_iso()),
    )
    row = conn.execute(
        "SELECT confidence, last_seen, evidence_count FROM issues WHERE id = ?",
        (issue_id,),
    ).fetchone()
    # max() for last_seen is valid: both are ISO-8601 UTC so lexicographic compare works
    conn.execute(
        "UPDATE issues SET confidence = ?, last_seen = ?, evidence_count = ? WHERE id = ?",
        (
            max(row["confidence"], det.confidence),
            max(row["last_seen"], det.captured_at),
            row["evidence_count"] + 1,
            issue_id,
        ),
    )
    conn.commit()


def set_issue_status(
    conn: sqlite3.Connection, issue_id: str, status: IssueStatus
) -> None:
    """Advance an issue's lifecycle status (new→verified→filed→in_progress→resolved, or
    rejected)."""
    conn.execute("UPDATE issues SET status = ? WHERE id = ?", (str(status), issue_id))
    conn.commit()


def list_issues(
    conn: sqlite3.Connection,
    cls: IssueClass | None = None,
    status: IssueStatus | None = None,
) -> list[dict]:
    """Issues as plain dicts (API/dashboard shape), newest activity first, optionally filtered."""
    sql = "SELECT * FROM issues"
    clauses, params = [], []
    if cls:
        clauses.append("class = ?")
        params.append(str(cls))
    if status:
        clauses.append("status = ?")
        params.append(str(status))
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY last_seen DESC"
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_issue(conn: sqlite3.Connection, issue_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    return dict(row) if row else None


def update_issue(conn, issue_id, *, status=None, severity=None, note=None):
    """Update an issue's status/severity/note with lifecycle validation; returns the row dict."""
    current = get_issue(conn, issue_id)
    if current is None:
        raise KeyError(issue_id)
    if status is not None:
        frm, to = (
            IssueStatus(current["status"]),
            IssueStatus(status),
        )  # ValueError on bad value
        if frm != to and not can_transition(frm, to):
            raise ValueError(f"Illegal transition {frm} -> {to}")
        conn.execute("UPDATE issues SET status = ? WHERE id = ?", (str(to), issue_id))
        _event(conn, issue_id, f"status:{to}")
    if severity is not None:
        sev = Severity(severity)  # ValueError on bad value
        conn.execute(
            "UPDATE issues SET severity = ? WHERE id = ?", (str(sev), issue_id)
        )
        _event(conn, issue_id, f"severity:{sev}")
    if note is not None:
        conn.execute("UPDATE issues SET note = ? WHERE id = ?", (note, issue_id))
        _event(conn, issue_id, "note", note)
    conn.commit()
    return get_issue(conn, issue_id)


def _event(conn, issue_id, event, detail=None):
    conn.execute(
        "INSERT INTO issue_events (id, issue_id, event, detail, at) VALUES (?,?,?,?,?)",
        (new_id("ev"), issue_id, event, detail, now_iso()),
    )


def issue_evidence_media(conn, issue_id):
    """media_path of the issue's earliest evidence photo, or None."""
    row = conn.execute(
        """SELECT r.media_path FROM issue_evidence e
           JOIN raw_detections d ON d.id = e.detection_id
           JOIN reports r ON r.id = d.report_id
           WHERE e.issue_id = ? ORDER BY e.added_at LIMIT 1""",
        (issue_id,),
    ).fetchone()
    return row["media_path"] if row else None


def seed_issues(conn, issues):
    """Insert issue rows if absent (idempotent by id). Returns count inserted."""
    inserted = 0
    for i in issues:
        exists = conn.execute(
            "SELECT 1 FROM issues WHERE id = ?", (i["id"],)
        ).fetchone()
        if exists:
            continue
        conn.execute(
            """INSERT INTO issues (id, class, status, lat, lng, confidence, severity,
               first_seen, last_seen, evidence_count, note)
               VALUES (:id,:class,:status,:lat,:lng,:confidence,:severity,
               :first_seen,:last_seen,:evidence_count,:note)""",
            {**i, "note": i.get("note")},
        )
        inserted += 1
    conn.commit()
    return inserted


if __name__ == "__main__":
    # Self-check: schema builds and a report round-trips through the queue.
    conn = get_conn(":memory:")
    init_db(conn)
    r = Report(
        id=new_id("rpt"),
        media_path="x.jpg",
        lat=18.52,
        lng=73.85,
        captured_at=now_iso(),
    )
    insert_report(conn, r)
    enqueue(conn, r.id)
    assert dequeue(conn) == r.id
    assert dequeue(conn) is None
    assert get_report(conn, r.id).lat == 18.52
    print("ok — schema builds, report insert/enqueue/dequeue round-trips")
