"""Shared data models for the pipeline. Frozen seam — do not change field names/types
without updating every stage that reads them.

Plain dataclasses + StrEnum (stdlib) rather than pydantic: these are internal records that
cross function boundaries, not request/response bodies. The FastAPI ingestion endpoint parses
multipart Form/File itself and constructs a Report.
"""

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class IssueClass(StrEnum):
    POTHOLE = "pothole"
    GARBAGE = "garbage"


class IssueStatus(StrEnum):
    NEW = "new"
    VERIFIED = "verified"
    FILED = "filed"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# Statuses that are still "open" for clustering: a new detection near an issue in one of these
# states is additional evidence, not a new issue. RESOLVED/REJECTED are terminal — a detection
# near a resolved issue starts a fresh one (the problem recurred).
OPEN_STATUSES: tuple[IssueStatus, ...] = (
    IssueStatus.NEW,
    IssueStatus.VERIFIED,
    IssueStatus.FILED,
    IssueStatus.IN_PROGRESS,
)


def now_iso() -> str:
    """Current UTC timestamp as an ISO-8601 string (the storage format for all timestamps)."""
    return datetime.now(UTC).isoformat()


def new_id(prefix: str) -> str:
    """A short unique id like 'rpt_9f3a2b7c' / 'det_...' / 'iss_...' / 'ev_...'."""
    return f"{prefix}_{secrets.token_hex(4)}"


@dataclass
class Report:
    """One citizen submission at intake (§2.1). `media_path` is the stored-file locator."""

    id: str
    media_path: str
    lat: float
    lng: float
    captured_at: str  # ISO-8601, when the media was captured (client-supplied)
    source: str = "upload"  # upload | dashcam | drone | capture-app
    user_id: str | None = None
    device_meta: dict = field(default_factory=dict)
    idempotency_key: str | None = None


@dataclass
class RawDetection:
    """One detection from the processing pipeline (§2.2), before geo-dedup. Immutable record."""

    id: str
    report_id: str
    cls: IssueClass
    confidence: float
    lat: float
    lng: float
    captured_at: str
    bbox: tuple[float, float, float, float] | None = None  # x, y, w, h (normalized)
    severity: Severity = Severity.MEDIUM
    clustered: bool = False


@dataclass
class Issue:
    """A geo-deduplicated issue (§2.3): many detections cluster into one of these."""

    id: str
    cls: IssueClass
    status: IssueStatus
    lat: float
    lng: float
    confidence: float
    severity: Severity
    first_seen: str
    last_seen: str
    evidence_count: int


# Allowed issue lifecycle transitions (reviewer/auto). RESOLVED/REJECTED are terminal.
TRANSITIONS: dict[IssueStatus, set[IssueStatus]] = {
    IssueStatus.NEW: {IssueStatus.VERIFIED, IssueStatus.REJECTED},
    IssueStatus.VERIFIED: {IssueStatus.FILED, IssueStatus.REJECTED},
    IssueStatus.FILED: {
        IssueStatus.IN_PROGRESS,
        IssueStatus.RESOLVED,
        IssueStatus.REJECTED,
    },
    IssueStatus.IN_PROGRESS: {IssueStatus.RESOLVED, IssueStatus.REJECTED},
    IssueStatus.RESOLVED: set(),
    IssueStatus.REJECTED: set(),
}


def can_transition(frm: IssueStatus, to: IssueStatus) -> bool:
    """True if moving an issue from `frm` to `to` is a legal lifecycle step."""
    return to in TRANSITIONS.get(frm, set())
