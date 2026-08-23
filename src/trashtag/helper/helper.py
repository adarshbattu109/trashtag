"""Helper functions and the canonical mock detection data for TrashTag.

ponytail: this mock list is the single source of truth for the HTTP API and the MCP
tools. The dashboard (app/static/dashboard.html) carries its own equivalent JS array
because the design spec requires a self-contained single file with no API dependency —
same issues, two representations, intentional rather than drift. When the data stops
being mock, delete the JS array and point the dashboard at /v1/issues.
"""

import logging

logger = logging.getLogger(__name__)


# Pune-area detections: mixed class, confidence, status, ward. Coordinates are real Pune
# neighbourhoods so the map reads as a populated city rather than lorem-ipsum. Keep this in
# sync with the MOCK_ISSUES array in dashboard.html (see module docstring).
MOCK_ISSUES = [
    {
        "id": "A-0442",
        "class": "pothole",
        "status": "new",
        "confidence": 0.91,
        "lat": 18.5204,
        "lng": 73.8567,
        "ward": "Shivajinagar",
        "severity": "high",
        "timestamp": "2026-08-23T07:42:00",
        "days_open": 0,
        "address": "FC Road, near Deccan Gymkhana, Shivajinagar",
    },
    {
        "id": "A-0441",
        "class": "garbage",
        "status": "new",
        "confidence": 0.87,
        "lat": 18.5089,
        "lng": 73.8256,
        "ward": "Kothrud",
        "severity": "medium",
        "timestamp": "2026-08-23T07:15:00",
        "days_open": 0,
        "address": "Paud Road, opp. Mahatma Society, Kothrud",
    },
    {
        "id": "A-0439",
        "class": "pothole",
        "status": "verified",
        "confidence": 0.94,
        "lat": 18.5314,
        "lng": 73.8446,
        "ward": "Shivajinagar",
        "severity": "high",
        "timestamp": "2026-08-22T19:03:00",
        "days_open": 1,
        "address": "JM Road, near Sambhaji Park, Deccan",
    },
    {
        "id": "A-0437",
        "class": "pothole",
        "status": "filed",
        "confidence": 0.88,
        "lat": 18.5074,
        "lng": 73.8077,
        "ward": "Kothrud",
        "severity": "medium",
        "timestamp": "2026-08-21T14:20:00",
        "days_open": 2,
        "address": "Karve Road, near Nal Stop, Kothrud",
    },
    {
        "id": "A-0435",
        "class": "garbage",
        "status": "new",
        "confidence": 0.79,
        "lat": 18.4636,
        "lng": 73.8682,
        "ward": "Dhankawadi",
        "severity": "high",
        "timestamp": "2026-08-23T06:48:00",
        "days_open": 0,
        "address": "Katraj-Kondhwa Road, near Katraj Lake",
    },
    {
        "id": "A-0433",
        "class": "pothole",
        "status": "new",
        "confidence": 0.83,
        "lat": 18.5679,
        "lng": 73.9143,
        "ward": "Nagar Road",
        "severity": "medium",
        "timestamp": "2026-08-23T05:31:00",
        "days_open": 0,
        "address": "Viman Nagar Road, near Phoenix Marketcity",
    },
    {
        "id": "A-0431",
        "class": "garbage",
        "status": "verified",
        "confidence": 0.90,
        "lat": 18.5018,
        "lng": 73.8636,
        "ward": "Bhavani Peth",
        "severity": "high",
        "timestamp": "2026-08-22T11:09:00",
        "days_open": 1,
        "address": "Swargate Chowk, near ST Depot",
    },
    {
        "id": "A-0428",
        "class": "pothole",
        "status": "resolved",
        "confidence": 0.86,
        "lat": 18.5793,
        "lng": 73.7389,
        "ward": "Hinjawadi",
        "severity": "medium",
        "timestamp": "2026-08-18T09:00:00",
        "days_open": 5,
        "address": "Hinjawadi Phase 1, near Rajiv Gandhi Infotech Park",
    },
    {
        "id": "A-0425",
        "class": "garbage",
        "status": "filed",
        "confidence": 0.81,
        "lat": 18.5645,
        "lng": 73.7769,
        "ward": "Aundh",
        "severity": "medium",
        "timestamp": "2026-08-20T16:44:00",
        "days_open": 3,
        "address": "Baner Road, near Balewadi Stadium",
    },
    {
        "id": "A-0422",
        "class": "pothole",
        "status": "rejected",
        "confidence": 0.62,
        "lat": 18.5158,
        "lng": 73.8785,
        "ward": "Camp",
        "severity": "low",
        "timestamp": "2026-08-22T21:12:00",
        "days_open": 1,
        "address": "MG Road, Camp — wet-road glare, not a pothole",
    },
    {
        "id": "A-0419",
        "class": "garbage",
        "status": "new",
        "confidence": 0.77,
        "lat": 18.4967,
        "lng": 73.9089,
        "ward": "Hadapsar",
        "severity": "medium",
        "timestamp": "2026-08-23T04:57:00",
        "days_open": 0,
        "address": "Hadapsar-Saswad Road, near Magarpatta",
    },
    {
        "id": "A-0415",
        "class": "pothole",
        "status": "in_progress",
        "confidence": 0.92,
        "lat": 18.5510,
        "lng": 73.8410,
        "ward": "Shivajinagar",
        "severity": "high",
        "timestamp": "2026-08-19T13:38:00",
        "days_open": 4,
        "address": "Model Colony, near Shivaji Housing Society",
    },
]


def list_issues(
    issue_class: str | None = None, status: str | None = None
) -> list[dict]:
    """Return mock issues, optionally filtered by class and/or status.

    Args:
        issue_class: Restrict to one detection class ("pothole"/"garbage"), or None for all.
        status: Restrict to one lifecycle status, or None for all.

    Returns:
        The matching issue dicts, in their canonical order.
    """
    issues = MOCK_ISSUES
    if issue_class:
        issues = [i for i in issues if i["class"] == issue_class]
    if status:
        issues = [i for i in issues if i["status"] == status]
    logger.info(
        "Listing %d issues (class=%s, status=%s)", len(issues), issue_class, status
    )
    return issues


def get_issue(issue_id: str) -> dict | None:
    """Return a single issue by its detection ID, or None if there is no such issue."""
    return next((i for i in MOCK_ISSUES if i["id"] == issue_id), None)


if __name__ == "__main__":
    # Self-check: filters compose, and get_issue round-trips a known ID.
    assert len(list_issues()) == len(MOCK_ISSUES)
    assert all(i["class"] == "pothole" for i in list_issues(issue_class="pothole"))
    assert list_issues(issue_class="garbage", status="filed") == [
        i for i in MOCK_ISSUES if i["class"] == "garbage" and i["status"] == "filed"
    ]
    assert get_issue("A-0442")["ward"] == "Shivajinagar"
    assert get_issue("NOPE") is None
    print(f"ok — {len(MOCK_ISSUES)} mock issues, filters and lookup consistent")
