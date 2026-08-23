# TrashTag V2 — Design Spec

**Status:** Draft for review. Covers the V2 feature set: live pipeline data on the dashboard, real submitted images, per-report updates, and a submit-time "is this actually a pothole/garbage" validation gate. Filing adapters are tracked separately (see `docs/research/*` and the portal-recommendation research).

---

## 0. Goal

Close the loop that V1 left open. Today the dashboard renders a hardcoded `MOCK_ISSUES` array and generated SVG evidence thumbnails; submitted reports enter the pipeline DB but are never processed automatically or shown. V2 makes a citizen submission flow **end to end and visible**: submit → validated → detected → deduped → appears on the dashboard with its **real photo** → a reviewer can **update** it.

## 1. Scope

In scope:
1. **Foundation** — wire the dashboard + `/v1/issues` to the live pipeline DB (retire the mock), plus a background worker so queued reports get processed.
2. **Real submitted images** — serve stored media; the docket card shows the actual photo, not the SVG stub.
3. **Per-report update** — `PATCH` endpoint + dashboard edit UI for status/severity/notes.
4. **Foreground validation gate** — synchronous detector pass at submit; reject photos where a pothole/garbage isn't the primary subject.
5. **Auto-review & scaling** — automatically verify high-confidence/corroborated issues so a human isn't the per-report bottleneck; humans review only the ambiguous minority and approve filings in batches.
6. **Detection-model selection UI** — a polyglot-style panel to pick/configure the vision detector (provider, host/port/model, key) at runtime, with a test-on-image action.
7. **Filing pipeline (assisted, form-based)** — `FilingAdapter`s for CPGRAMS (+ Swachhata for garbage), umbrella-account filing, status polling, and a BeautifulSoup/headless form-fill pipeline; human approves batches.

Out of scope (separate tracks): face/plate blurring + public map, fine-tuned YOLO, on-device capture app, resolution-photo auto-verification (Phase 3).

---

## 2. Foundation: live data + background worker

### 2.1 Dashboard & API read live issues
- `read_issues` / `read_issue` in `app/serve.py` switch from `helper.list_issues` (mock) to `db.list_issues` / `db.get_issue` (pipeline DB). Keep the 422-on-unknown-filter behaviour.
- The dashboard fetches `GET /v1/issues` on load (and after actions) instead of embedding `MOCK_ISSUES`. The docket queue, map markers, and filed log all render from the live response.
- **Test isolation:** the API reads `db.get_conn()` (honours `TRASHTAG_DB`); tests point it at a temp DB, so this doesn't break the existing suite. The `helper.MOCK_ISSUES` becomes seed/demo data loadable into the DB via a small `seed` helper (so the dashboard isn't empty on a fresh install).

### 2.2 Issue shape gap (decision)
Pipeline issues expose `{id, class, status, lat, lng, confidence, severity, first_seen, last_seen, evidence_count}`. The dashboard also shows `address`, `ward`, and `days_open`.
- **Recommendation:** reverse-geocode `lat/lng → address + ward` at ingestion via OSM Nominatim (rate-limited, cached on the report), stored so the dashboard and any future filing adapter reuse it (this also seeds the §2.4 jurisdiction gate). `days_open` is derived from `first_seen`.
- **Fallback if geocoding is deferred:** show coordinates and "ward: —"; the UI must not assume those fields exist. This keeps the feature shippable without the external call.

### 2.3 Background worker
Submitted reports must be processed without a manual trigger.
- A FastAPI **lifespan background task** drains the queue on an interval (e.g. every few seconds): `dequeue → process_one → cluster_pending`. Single-process, cooperative; documented as the zero-infra stand-in for a Celery/Kafka worker.
- Because validation (§5) already runs the detector synchronously at submit, the worker's job for the submit path is mainly **dedup**; the validation pass's detections are persisted at submit so the detector never runs twice for the same report. The worker still covers any non-submit sources and retries.

---

## 3. Real submitted images

- **Endpoint:** `GET /v1/issues/{id}/evidence` → `FileResponse` of the issue's primary evidence photo (resolve issue → its `issue_evidence` → the seed detection's `report` → `report.media_path` → `MediaStore.open`). Returns 404 if the issue or media is missing. `GET /v1/reports/{id}/media` may back it.
- **Dashboard:** the docket card's evidence strip becomes `<img src="/v1/issues/{id}/evidence" …>` with a graceful placeholder (the existing SVG) on load error, so mock/seed issues without media still render.
- **Privacy:** the internal ops dashboard may show raw photos; the **face/plate blur gate remains mandatory before any public-map exposure** (unchanged, out of scope here). Note in code that this endpoint is internal-only.

---

## 4. Per-report update

- **Endpoint:** `PATCH /v1/issues/{id}` accepting a partial body: `status`, `severity`, and an optional freeform `note`. Validates status transitions against the lifecycle (`new → verified → filed → in_progress → resolved`; any open state `→ rejected`); rejects illegal transitions with 422 and a clear message.
- The existing **Verify / Reject / Merge** actions become `PATCH` calls (`verified` / `rejected` / merge stays its own op). Add an inline **edit** affordance on the docket card: change severity, add a note; the card reflects the new stamp/state and the pending count updates.
- `db` gains `update_issue(conn, id, **fields)` and an `allowed_transition(from, to)` guard; `set_issue_status` already exists.
- **Audit:** record who/when for updates in a lightweight `issue_events` row (reviewer action trail). Reviewer identity is out of scope (no auth yet) → record `source="ops-dashboard"` for now.

---

## 5. Foreground validation gate (synchronous at submit)

**Behaviour:** during `POST /v1/reports`, after storing the media, run the configured detector on the photo **synchronously**. Accept only if a pothole or garbage dump is the **primary subject**.

- **Primary-subject check:** extend the VLM prompt to return, per detection, whether the issue is the main subject (e.g. an `is_primary` flag, or estimate its bbox-area share ≥ a threshold). Accept if ≥1 detection is primary and above the confidence gate.
- **Reject path:** `422` with the dashboard-voice message: `This doesn't look like a pothole or garbage dump. Capture the issue clearly in the foreground and try again.` No report row is persisted (or it's persisted with `status=rejected` and not enqueued — decision: **do not persist** rejected submissions, to avoid junk storage; the citizen just retries).
- **Reuse the detections:** the validation pass's detections are the report's detections — persist them so §2.2 processing isn't repeated; the background worker then only dedups.
- **Detector-outage safety:** if the detector errors/times out (e.g. VLM unreachable, HF credits depleted — a real case), **do not reject the citizen**. Accept the report, mark it `unvalidated`, and let a human see it in a review lane. Losing a legitimate report because our detector is down is worse than accepting an occasional bad one.
- **Stub caveat:** the deterministic stub can't truly judge content, so with `TRASHTAG_DETECTOR=stub` the gate is effectively permissive (documented). Meaningful validation requires a real VLM (`TRASHTAG_DETECTOR=vlm`, e.g. Qwen3-VL). This is acceptable: dev/tests use the stub; deployments that want the gate enable the VLM.
- **Cost/latency:** one detector call per submit. Acceptable for an interactive submit (the citizen waits a moment). The frame-dedup gate (`frames.py`) already prevents burst/video spam upstream.

---

## 5b. Auto-review & scaling (removing the human bottleneck)

**Problem:** at scale a human cannot look at every report. **Verification is automated; filing keeps a human at batch granularity.** Auto-review never files — it only decides *real / not-real / uncertain*.

### Lanes (applied after dedup, §2.3)
After `cluster_pending` sets/updates an issue, an `auto_review(conn, issue)` step routes it:
- **Auto-verified** → `status = verified`, skips the human queue, when it clears the policy:
  `evidence_count >= AUTOVERIFY_MIN_EVIDENCE` (independent-report corroboration — the architecture's "confirmed (N reports)") **OR** `confidence >= AUTOVERIFY_MIN_CONFIDENCE`.
- **Human-review** → stays `new` in the review queue, for the ambiguous minority: confidence between the detector gate and `AUTOVERIFY_MIN_CONFIDENCE`, single evidence, or conflicting class at one location.
- **Auto-rejected** → already handled upstream by the §5 foreground-validation gate; non-issues never reach here.

### Second signal (optional) for single-evidence, high-confidence
Before waiting for corroboration, an **independent LLM-judge / second-VLM pass** can adjudicate a single high-confidence detection ("is this really a pothole/garbage, is it the primary subject, how severe?"). Use a *different* model or prompt from the detector to avoid correlated errors. Agree → auto-verify; disagree → human lane. Opt-in (`TRASHTAG_AUTOREVIEW_JUDGE=on`).

### Batch filing approval (the filing bottleneck)
Verified issues collect into **filing batches** grouped by authority / ward / class. A reviewer approves a *batch* in one action ("file these 48 verified potholes in Ward 12") rather than one-by-one — a human stays accountable at the filing step (batch granularity), preserving the spirit of *human-presses-send*. Filing itself still respects the jurisdiction gate, the "probable match, verify against tender documents" wording, and the per-class adapter (Swachhata for garbage, CPGRAMS for potholes, city overrides) — see `docs/research/india-filing-portal-recommendation.md`.

### Policy, audit, and safety
- **Configurable thresholds:** `TRASHTAG_AUTOVERIFY_MIN_EVIDENCE` (default 3), `TRASHTAG_AUTOVERIFY_MIN_CONFIDENCE` (default 0.90). Set evidence to a huge number to force everything to the human lane for a cautious launch.
- **Audit:** every auto-decision writes an `issue_events` row naming the policy that fired.
- **Sampling / spot-check:** a dashboard view surfaces a random %% of auto-verified issues so you can audit machine decisions and tune thresholds; if spot-checks find errors, raise thresholds or route more to human.
- **Guardrails:** never auto-verify a `rejected` issue; conflicting-class detections at one location always go to a human; auto-verify is verification only and can never trigger a filing on its own.

### Impl & tests
- `dedup` already yields `evidence_count` + `confidence`; add `auto_review.py` with `auto_review(conn, issue, policy)` and a `filing_batches(conn)` grouper; the background worker (§2.3) runs `auto_review` after `cluster_pending`.
- Tests (offline): policy routing (N / T thresholds → correct lane), guardrails (conflicting class → human; rejected never verified), mocked second-VLM judge (agree/disagree), batch grouping by authority/ward, and audit rows written.

## 5c. Detection-model selection UI (polyglot-style)

Mirror [polyglot](https://github.com/adarshbattu109/polyglot)'s "Model connection" panel + `/verify` flow, for TrashTag's **vision detector**. The `VLMDetector` already takes `host/port/path/model/api_key`, so this is mostly a UI + two small endpoints over the existing seam.

> **Deployment posture — config is NOT for end users.** Unlike polyglot (a single-user local tool where the caller supplies the endpoint), deployed TrashTag has three audiences: **citizens** (Submit flow only), **ops reviewers** (review/verify/update issues only), and **admins/operators** (model + system config). Model configuration is an admin/infra concern and must never be exposed to citizens or general reviewers.
>
> **Two supported modes, in order of preference:**
> 1. **Config-driven (production default):** the detector is set purely by env vars / a config file (`TRASHTAG_DETECTOR`, `TRASHTAG_VLM_*`). **No runtime config UI or write endpoint is exposed.** This is the default in any real deployment.
> 2. **Admin panel (optional):** the polyglot-style runtime selection UI below is available **only behind an admin auth boundary** and a feature flag `TRASHTAG_ALLOW_RUNTIME_CONFIG` (default **off**). It requires authentication + an `admin` role — see the access-control note. Until auth exists, the write endpoints stay dev/loopback-only and off by default.
>
> The provider **prefill/`GET /config`** and the picker described below are the *admin-panel* surface; they are gated, not part of the citizen or reviewer UI.

- **Providers list** (`constants.py`, like polyglot's `PROVIDERS`): known vision-capable OpenAI-compatible endpoints with prefill (`id, label, host, port, path, model, needs_key, note`) — e.g. **Ollama (local)** `localhost:11434` `qwen3-vl:2b` no-key; **Ollama Cloud** `ollama.com:443`; **HF Inference Router** `router.huggingface.co:443` `Qwen/Qwen3-VL-30B-A3B-Instruct` key; **vLLM (local)** `127.0.0.1:8001`; **Alibaba DashScope**; **OpenRouter** `openrouter.ai:443 /api/v1`; **Custom**. Plus the built-in **Stub** (offline/dev). Adding a provider is a dict entry, not code.
- **`GET /config`** returns the active detector config (`host/port/path/model` + `providers` + selected `detector`), **deliberately omitting `api_key`** — echoing a credential back is a leak (mirror polyglot; assert it's absent in tests).
- **Dashboard panel "Detection model":** choose a provider → prefills the fields; enter a key if `needs_key`; **Save** applies it. Shows the active model in the status strip.
- **`POST /config/detector`** (admin-only, flag-gated) sets the server's active detector in-memory (rebuilds `VLMDetector` / selects the stub) — switch local Ollama ↔ HF ↔ cloud without a restart. Requires `admin` role + `TRASHTAG_ALLOW_RUNTIME_CONFIG=on`; returns 403/404 otherwise. **Loopback-only until auth ships.**
- **`POST /config/detector/test`** (admin-only, the vision `/verify`): runs the chosen config's `detect()` on an uploaded/sample image and returns the detections or a clear error — confirm a model works before making it active.
- **Persistence:** in-memory when set via the admin panel (resets on restart); the durable source of truth remains env/config file. A persisted settings store is a later add.
- **Security (add to SECURITY.md):** a runtime-configurable detector connects wherever it's told → SSRF by design, acceptable **only** because the server binds loopback; any port other than 443 sends the image *and key* in the clear; `api_key` is write-only and never returned by `/config`. Same posture as polyglot's caller-supplied endpoint.

Tests: `/config` omits `api_key`; `POST /config/detector` changes the active detector; the test endpoint runs a mocked `detect`; the provider list is served.

## 5d. Access control (prerequisite for deployment)

The admin/config split above only means something with authentication, which TrashTag does not have yet (V1 binds loopback, no auth). V2 introduces **three roles**:

| Role | Can | Cannot |
|---|---|---|
| **Citizen** | Submit reports (Submit flow) | See the review queue, issues API, or any config |
| **Reviewer (ops)** | View/verify/update/merge issues, approve filing batches | Configure the detector or system settings |
| **Admin / operator** | Everything + detector/model config (§5c), thresholds (§5b), system settings | — |

- Until an auth layer exists, config endpoints stay **loopback-only + flag-off**, and the review dashboard assumes a trusted operator. **Auth + RBAC is its own foundational task** (session tokens / SSO, role checks on endpoints) and blocks the admin panel and any public/citizen-facing deployment.
- `GET /config` and all `/config/*` endpoints require the `admin` role once auth lands; the citizen Submit flow needs none of them.
- This is called out in SECURITY.md alongside the existing "internal ops tool, bind loopback" posture.

## 5e. Filing pipeline (assisted, form-based)

The heaviest track. Full detail + decisions live in [`docs/research/india-filing-portal-recommendation.md`](research/india-filing-portal-recommendation.md); this section is the build shape. Everything below keeps the **human-presses-send batch gate**.

### Adapters & routing
- `FilingAdapter` interface + a **class→adapter router**. **Default: CPGRAMS for both** classes (leaner, one integration). Add **`SwachhataAdapter` (the MoHUA app) for garbage** when its **resolution-photo loop** (before/after + citizen verify) justifies a second partnership. City adapters (ICMC, etc.) as location overrides.

### Shared filing infra (built once — most of the code)
- Umbrella-account **session management**; **OTP broker** (email-OTP preferred, session-level to minimise events); **status polling** under the one umbrella account → feeds the issue lifecycle; **complaint-packet generator** (subject <100 chars, description <1000, ≤5 PDFs ≤4 MB — per architecture §2.4); **batch-approval UI**.
- **Identity:** file under the umbrella account; citizen PII is never included; fully-anonymous reports supported.

### Form-fill pipeline
Neither portal exposes a public API, so filing is a scrape-and-fill assist until a partnership lands:
- **Server-rendered HTML portals:** `httpx`/`requests` GET the form → **BeautifulSoup** parses the fields, hidden **CSRF/view-state** tokens, and dropdown option values (category, ward) → map our issue onto them → build the prefilled submission. BS4 also drives **status-page scraping**.
- **JS-SPA portals** (CPGRAMS pages looked SPA-like in research — BS4 won't see a JS-rendered form): escalate to a **headless browser (Playwright)**. A per-portal spike decides server-rendered vs SPA — this picks BS4-only vs BS4+headless.
- **OTP + CAPTCHA stay human/assisted:** the pipeline prefills and drives *up to* submission; a human clears CAPTCHA + supplies OTP (one per batch/session) and approves the batch. **No CAPTCHA-solving** (decision on record — circumventing a government portal's anti-bot control is out of bounds; CAPTCHA is per-batch, so it isn't the scale bottleneck).
- **Durable unlock:** a negotiated **API/partnership** replaces the whole scrape+form path with an API client — pursue per portal.

### Effort & sequencing
- The **shared infra is most of the code**, built once. A second adapter is only ~**30–50%** incremental *code* — but the **non-code** cost roughly **doubles per portal** (separate partnership, umbrella registration, ToS review, and a second form-fill flow to maintain; Swachhata also has uptime uncertainty).
- **Sequence:** shared infra + **CPGRAMS first** (covers both classes as fallback) → add **SwachhataAdapter** for garbage later for the resolution loop → city overrides where proven.

### Tests
Adapter router (class→adapter); packet generation respects field limits; **BS4 form-parse against a saved sample HTML fixture** (offline); status-parse against a saved status page; the assisted flow **stops at OTP/CAPTCHA** (no auto-submit in tests).

## 6. Microcopy (per the dashboard voice)

- Rejected submit: `This doesn't look like a pothole or garbage dump. Capture the issue clearly in the foreground and try again.`
- Detector down: `Couldn't auto-check your photo right now — submitted for manual review.`
- Update conflict: `Can't move a resolved detection back to new.` (state the rule, name the next action.)

---

## 7. Testing

- API: `PATCH` status transitions (legal + illegal→422); `GET …/evidence` (200 with bytes, 404 missing); `read_issues` now reading the DB (seed a temp DB, assert filters).
- Validation gate: monkeypatch the detector — returns a primary pothole → 202; returns `[]` → 422 (not persisted); raises → 202 `unvalidated`. Stub → permissive.
- Worker: enqueue a report → run one worker tick → issue appears via `GET /v1/issues`.
- All offline (detector + geocoder mocked); no network in CI.

---

## 8. Sequencing & dependencies

1. **Foundation** (§2) — live-data read + background worker + (optional) reverse-geocode. Everything else depends on this.
2. **Real images** (§3) — needs live data + media store.
3. **Per-report update** (§4) — needs live data.
4. **Foreground validation** (§5) — independent of the dashboard; needs the detector (VLM for real behaviour). Reuses detections into the pipeline.
5. **Auto-review** (§5b) — runs in the worker right after dedup; needs `evidence_count`/`confidence` (already there) and, if the judge option is on, a second VLM. The **batch-filing** UI depends on filing adapters existing (separate track), so batch approval ships after the first adapter; auto-*verify* ships with the worker.
6. **Detection-model selection UI** (§5c) — independent; pairs naturally with the foreground-validation work since both exercise the live detector. Ship once the VLM path is in regular use.
7. **Filing** (§5e) — the heaviest track and gated by per-portal spikes + partnership. Build the **shared filing infra first** (session/OTP/status/packet/batch-UI — an extensible foundation every adapter reuses), then `CPGRAMSAdapter` (both classes), then `SwachhataAdapter` (garbage) and city overrides as value/partnerships justify. Realistically V2.2+.

---

## 9. Open decisions for review

1. **Reverse-geocoding** at ingestion (Nominatim, adds an external call + cache) vs. showing coordinates only for now.
2. **Rejected submissions:** discard entirely vs. persist as `rejected` for abuse analytics. (Spec currently: discard.)
3. **Worker model:** in-process lifespan task (simplest) vs. a separate `trashtag-worker` entry point (cleaner for scale). (Spec currently: lifespan task.)
4. **Primary-subject signal:** VLM `is_primary` flag vs. bbox-area threshold (needs the bbox upgrade Qwen3-VL supports).
5. **Auto-verify thresholds:** starting values for `AUTOVERIFY_MIN_EVIDENCE` (3) and `AUTOVERIFY_MIN_CONFIDENCE` (0.90) — and whether to launch conservative (everything to the human lane) then loosen as spot-checks build trust.
6. **Second-VLM judge:** ship the independent judge for single-evidence auto-verify in V2, or start corroboration-only (N reports) and add the judge later.
7. **Detector config scope:** a single global server-side active detector (recommended for a single-operator internal tool) vs. per-session/per-user selection; and where the `api_key` lives (env only vs. in-memory runtime settings). **Default per your note: config-driven (env/file); runtime admin panel is opt-in + flag-gated.**
8. **Auth/RBAC (§5d):** ship it in V2 (blocks the admin panel + any citizen-facing deployment) vs. defer and keep the whole thing loopback/trusted-operator with config-driven models only. What auth mechanism (session tokens, SSO/OIDC, API keys per role)?
9. **Filing tech per portal (§5e):** server-rendered (BeautifulSoup + `httpx`) vs. JS-SPA (headless Playwright) — decided by a per-portal spike; and whether to invest in the form-fill pipeline now vs. wait for an API/partnership before building any filing.
