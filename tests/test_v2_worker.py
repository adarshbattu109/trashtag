from trashtag.pipeline import db
from trashtag.pipeline.models import Report, new_id, now_iso
from trashtag.pipeline.store import FilesystemMediaStore
from trashtag.pipeline.worker import run_worker_tick


class _FixedDetector:
    def detect(self, media, lat, lng, captured_at, report_id):
        from trashtag.pipeline.models import IssueClass, RawDetection, Severity

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


def test_worker_tick_processes_and_clusters(tmp_path):
    conn = db.get_conn(":memory:")
    db.init_db(conn)
    store = FilesystemMediaStore(tmp_path)
    store.save(b"img", "rpt_1_p.jpg")
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
    db.enqueue(conn, "rpt_1")

    assert run_worker_tick(conn, store, _FixedDetector()) == 1
    assert len(db.list_issues(conn)) == 1
    assert run_worker_tick(conn, store, _FixedDetector()) == 0  # queue drained
