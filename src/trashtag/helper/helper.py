"""Helper functions and mock detection data for TrashTag.

ponytail: MOCK_ISSUES is seed data loaded once into the pipeline DB via mock_issue_rows().
The HTTP API and MCP tools read from the live DB, not this array. The dashboard fetches
/v1/issues live. When seeding is no longer needed, delete MOCK_ISSUES and mock_issue_rows().
"""

import logging

logger = logging.getLogger(__name__)


# Pune-area detections: mixed class, confidence, status, ward. Coordinates are real Pune
# neighbourhoods so the map reads as a populated city. This is seed data only.
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


def mock_issue_rows():
    """MOCK_ISSUES mapped to the pipeline issues-table shape (for seeding the DB)."""
    return [
        {
            "id": i["id"],
            "class": i["class"],
            "status": i["status"],
            "lat": i["lat"],
            "lng": i["lng"],
            "confidence": i["confidence"],
            "severity": i["severity"],
            "first_seen": i["timestamp"],
            "last_seen": i["timestamp"],
            "evidence_count": 1,
        }
        for i in MOCK_ISSUES
    ]


if __name__ == "__main__":
    # Self-check: mock_issue_rows() produces the expected number of rows with required keys.
    rows = mock_issue_rows()
    assert len(rows) == len(MOCK_ISSUES)
    required_keys = {
        "id",
        "class",
        "status",
        "lat",
        "lng",
        "confidence",
        "severity",
        "first_seen",
        "last_seen",
        "evidence_count",
    }
    assert all(required_keys <= row.keys() for row in rows)
    print(
        f"ok — {len(MOCK_ISSUES)} mock issues, mock_issue_rows() produces valid schema"
    )
