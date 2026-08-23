"""The ingestion → processing → dedup pipeline (architecture plan §2.1–§2.3).

Zero-infra slice: filesystem media store + SQLite (with a haversine distance for spatial
clustering) instead of MinIO/Kafka/PostGIS. The seams (`models`, `geo`, `store`, `db`,
`interfaces`) are shared and frozen; each stage builds against them:

- `ingest`  — §2.1 the `POST /v1/reports` intake + media store + enqueue
- `process` — §2.2 dequeue → detect (stub Detector) → confidence gate → raw_detections
- `dedup`   — §2.3 cluster raw_detections into geo-deduplicated issues + lifecycle
"""
