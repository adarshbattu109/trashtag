# TrashTag — Architecture & Build Plan

*"Tag the trash. Flag the roads."*

**Status:** Living spec, handoff-ready. Covers Phase 1 (citizen upload + ops review) and Phase 2 (native capture app + public map overlay). Companion document: `civic-vision-dashboard-design-spec.md` (ops dashboard UI spec).

**Naming note:** the product is named TrashTag, covering both garbage-dump and pothole reporting — the tagline exists specifically to make the pothole scope explicit, since "trash" alone reads as litter-only to a cold audience. Keep the tagline paired with the name in any external-facing material (app store listing, pitch deck, public map footer).

---

## 0. Product summary

TrashTag is a platform that collects pothole and garbage-dump evidence from multiple citizen sources (photo/video upload, dedicated capture app, dashcams, drones), runs AI detection, deduplicates geospatially, and helps get real issues filed with the responsible municipal authority — with contractor/tender accountability where public contract data exists.

---

## 1. High-level flow

```
Citizen Sources → Ingestion API → Processing Pipeline → Geo-DB → Dedup/Aggregation
     → Reporting/Filing Layer → Ops Dashboard (internal) + Public Map (external)
```

---

## 2. Phase 1: Ingestion, Processing, Filing

### 2.1 Ingestion Layer (multi-source intake)
Source-agnostic upload gateway — every source hits the same contract.

- **API:** FastAPI, `POST /v1/reports` (multipart: media + GPS + device metadata + optional user_id)
- **Sources:** mobile photo/video upload, dashcam companion app, drone batch upload, (Phase 2) native capture app, (future) fleet dashcam webhook feeds
- **Media handling:** async — upload → object storage (S3/MinIO) → event to queue (Kafka/Redis Streams/SQS). Keeps ingestion fast regardless of media size.
- **Auth:** JWT per device/citizen account, rate-limited per user
- **Idempotency:** hash media + geohash + timestamp window to reject obvious duplicate uploads at ingestion

### 2.2 Processing Pipeline (async workers)
Stateless worker pool (Celery/RQ or Kafka consumers on K8s), triggered by queue events.

- **Video:** extract frames at 1–3 fps (OpenCV/ffmpeg); GPS/timestamp interpolated per frame
- **Per-frame steps:**
  1. Preprocess (resize, EXIF GPS extraction, day/night brightness normalization)
  2. YOLO inference (fine-tuned pothole/garbage classes), batched on GPU workers
  3. Lightweight tracker (ByteTrack/IOU) across video frames to collapse one physical issue seen across many frames into a single detection
  4. Confidence gate — drop low-confidence, flag borderline for human review queue
  5. Severity/size estimation (bbox area heuristic or small classifier head)

### 2.3 Geospatial Deduplication & Aggregation
- **Store:** PostgreSQL + PostGIS, geo-indexed
- **Clustering:** new detection within ~10–15m of an existing open issue of the same class → merged as additional evidence, not a new record
- **Issue lifecycle:** `new → confirmed (N reports) → filed → in_progress → resolved`
- **Schema:**
  - `raw_detections` — per-frame, immutable, source-tagged
  - `issues` — deduplicated, clustered, geo-indexed, status
  - `issue_evidence` — many detections → one issue, audit trail

### 2.4 Reporting/Filing Layer

**Primary filing target: CPGRAMS** (Centralised Public Grievance Redress and Monitoring System). Chosen over city-by-city portals as the default adapter because it's a single, standardized, national-scope system rather than something we'd need to rebuild per city — and because city apps have shown themselves fragile (PMC's Road Mitra went dark for months in 2026 over an unpaid SMS gateway package).

Why it fits well:
- One portal covering Central Ministries and (for subscribed departments) most states, instead of one integration per municipality
- Built-in auto-routing to the correct last-mile Grievance Redressal Officer, and a unique registration ID issued at submission for status tracking — solves the jurisdiction/routing problem CPGRAMS-adjacent city apps make us solve ourselves
- A real SLA and escalation structure (30-day resolution target, mandatory feedback, 5-level appeal path) — gives our "resolved" status a genuine external verification signal instead of an internal heuristic
- Some states/ministries already have **API-based integration** rather than form-only submission — this needs to be confirmed per state before deciding the adapter's submission mechanism (see spike below)

**Technical spike — do this before building the adapter:** determine whether CPGRAMS (or the relevant state's integrated portal) exposes a genuine submission/status API, or whether filing has to go through the citizen-facing web form. This single finding determines whether `CPGRAMSAdapter` is a real API client or a packet-generator-plus-guided-form-fill. Check both the national CPGRAMS system and the specific state(s) we're piloting in, since integration maturity varies by state.

**Format constraints to bake into complaint generation now** (from the CPGRAMS submission form, regardless of API vs. manual path):
- Subject line: under 100 characters
- Description: under 1,000 characters initially (can extend via attachment)
- Supporting documents: PDF, max 4MB each, up to 5 files
- A registration/tracking ID is returned on submission — store this against the `issue` record as the resolution-tracking key, and poll/ingest status transitions (`Submitted → Under Examination → Action Initiated → Resolved/Closed`) back into our own issue lifecycle (§2.3) rather than maintaining a parallel one

**General filing design (applies regardless of API access):**
- Generates structured complaint (photo, GPS, reverse-geocoded address, description, severity) per confirmed issue, respecting the format constraints above
- **Tier 1 (MVP):** ops dashboard, human reviews and submits (directly via API if available, or via a pre-filled guided form-fill if not), or exports CSV/GeoJSON batches
- **Tier 2 (partnership):** negotiated data-feed integration with a municipal smart-city cell for cities/issue-types CPGRAMS doesn't cover well — business development, not engineering
- Filing logic is pluggable (`FilingAdapter` interface): `CPGRAMSAdapter` as the default/fallback for most locations, with city-specific adapters (PMC Road Mitra, PCMC, etc.) only where CPGRAMS coverage or routing proves weak in practice
- **Human-in-the-loop always.** The system drafts; a person sends or confirms submission. No adapter auto-submits without review — a deliberate, non-negotiable design choice (see §5)
- **Jurisdiction gate:** if the reverse-geocoded location can't be confidently matched to a known authority boundary, the issue is marked "Outside coverage" rather than guessing a recipient (see §5) — CPGRAMS's own auto-routing may reduce how often we need this, but it stays as a safety net for locations it can't resolve either
- **Contractor/tender accountability (where data exists):** cross-reference issue location against public procurement/contract data to surface a probable responsible contractor and tender number, attached as supporting context in the CPGRAMS description/attachment. Always worded as *"probable match, verify against tender documents"* — never asserted as fact (see §5)

---

## 3. Phase 2: Native Capture App + Public Map

### 3.1 Citizen Capture App

**Sensors and roles:**

| Sensor | Purpose |
|---|---|
| GPS | Geotag captures; trigger capture on distance-moved rather than fixed fps |
| Camera | Still-frame capture API where available (sharper than preview-frame grabs) |
| Accelerometer | Detect real bump/jolt events to trigger candidate capture in passive drive mode — reduces inference volume vs. polling every N meters |
| Gyroscope (optional) | Filter phone-handling vibration from real road jolts, simple threshold + debounce |

**Capture modes:**
1. **Single-shot report** — manual photo, tap submit
2. **Passive drive mode** — phone mounted, accelerometer-triggered capture, GPS-tagged, queued for background upload; citizen doesn't have to actively look for issues

**On-device pre-filter:** run a lightweight YOLO-Nano pass on-device before upload, so only frames with a plausible detection get sent to the backend for confirmation. This is the key lever that keeps inference cost near-zero at scale for continuous passive capture — full server-side inference on every frame does not scale to many simultaneous citizen drivers.

**Upload:** background-queued, resumable, offline-tolerant (dashcams/drones often operate in low-signal areas), syncs to the same `POST /v1/reports` contract as every other source — this is just another source type, not a new pipeline.

### 3.2 Public Map Overlay

Two distinct views — do not conflate them:

- **Ops dashboard map** (internal, reviewers) — see `civic-vision-dashboard-design-spec.md`
- **Public map** (external, citizens/press/officials) — read-only, trust/transparency layer

**Public map spec:**
- Tech: OpenStreetMap + Leaflet — no API billing/quota risk at citizen scale, visually consistent with the product's own design language rather than inheriting Google's
- Shows confirmed issues only; status (reported/filed/resolved); no raw evidence exposing incidental private-property/people details
- Density clustering (zoom-dependent, reuses PostGIS clustering from §2.3)
- Color-coded by class: hazard-yellow = pothole, waste-green = garbage (consistent with dashboard token system)
- Click → issue detail: photo, status, days-open, filed date — **no reporter identity**
- Optional ward-level heatmap toggle for civic-accountability visibility ("which areas are worst")

**Privacy requirement — build before public launch, not after:** citizen photos may incidentally capture faces or license plates. Add a face/plate-blurring pass to the processing pipeline (§2.2) before any image is eligible for public map display. This is a hard gate, not a nice-to-have.

---

## 4. Tech Stack Summary

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | async-native, fast to iterate |
| Queue | Kafka or Redis Streams | decouples ingestion from inference |
| Inference | YOLOv8/26-N via ONNX Runtime/TensorRT | fine-tuned pothole/garbage classes, edge-deployable |
| On-device pre-filter | YOLO-Nano (mobile export) | cost control for passive capture mode |
| Object storage | S3-compatible (MinIO/AWS S3) | cheap, scalable media |
| DB | PostgreSQL + PostGIS | geospatial queries, mature tooling |
| Public map | Leaflet + OpenStreetMap | no billing risk, on-brand |
| Orchestration | Kubernetes | independent scaling of API vs. inference workers |
| Ops dashboard | Streamlit (MVP) → React later | fast to ship |
| Observability | Prometheus + Grafana | queue depth, inference latency, detection rates |

---

## 5. Design decisions borrowed from prior art (with credit)

**[coding-parrot/pothole-reporter](https://github.com/coding-parrot/pothole-reporter)** — an on-device Android pothole reporter for Bengaluru by Gaurav Sen (MIT license). Built as a personal single-city tool (no backend, VLM-per-frame via OpenAI API, human presses send). Several of its design decisions are worth adopting even though our platform's scale and architecture differ substantially:

- **Jurisdiction-aware routing with an explicit "outside coverage" state** rather than guessing a recipient when location confidence is low — adopted in §2.4.
- **Contractor/tender matches always worded as "probable match, verify against tender documents"** rather than stated as fact — adopted in §2.4. Protects against wrongly implicating a contractor from noisy public contract data.
- **Distance-based deduplication (~15m radius)** — validates our independently-designed PostGIS clustering approach in §2.3; same idea, different (server-side, cross-citizen) scale.
- **Human always presses send; the system never auto-files** — adopted as a hard rule in §2.4. Legally and ethically the right default until a real filing partnership exists.
- **GPS-distance-triggered capture (not fixed fps) and day/night brightness normalization** — adopted in §3.1 / §2.2.
- **On-device human-labelled frame review/export**, with the model's verdict shown *after* the human's own label to avoid biasing the reviewer — worth adopting later as a pattern for building our own fine-tuning dataset over time (not yet in scope above, flag for Phase 3).

Their own roadmap independently identifies the same scaling gap our architecture is built to solve — a local YOLO pre-filter for near-zero-cost continuous capture — which is a solid design tell.

Not adopted: single-city hardcoded jurisdiction/contract data, no-backend architecture, and VLM-per-frame detection — all reasonable for a single-developer single-city tool, but don't hold up for a multi-source, multi-city, multi-citizen platform. Attribution belongs in the product README and in any public-facing "how it works" page, not just this internal doc.

---

## 6. Phased Build Plan

1. **Phase 1 (MVP, single city):** mobile upload → inference → PostGIS dedup → Streamlit ops dashboard with manual export
2. **Phase 2:** native capture app (accelerometer-triggered passive mode, on-device pre-filter), public map overlay, jurisdiction gate, contractor/tender matching
3. **Phase 3:** drone batch ingestion, severity classification, resolved-status auto-verification, human-labelled dataset review tooling for continuous model improvement
4. **Phase 4:** municipal data-partnership integration, multi-city adapter framework, pan-region jurisdiction/contract data
