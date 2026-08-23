# TrashTag — Project Status (resume here)

> **Purpose:** the single doc to read after cloning on a fresh machine to pick up
> exactly where work left off. Everything needed to resume lives in the repo — no
> external notes or local ledgers are required.

_Last updated: 2026-08-23._

---

## TL;DR

- **`main`** (`1045645`) — V1: the ops dashboard over mock data, ingestion → processing →
  10m geo-dedup pipeline, MCP server, citizen capture. Runnable, tested.
- **`v2`** (`60690d0`, pushed to origin) — **V2.0 "visible loop" is COMPLETE, reviewed, and
  verified end-to-end.** This is the active branch. `git checkout v2` to continue.
- **Not yet done:** V2.0 is not merged to `main` (no PR opened yet). V2.1, V2.2, and the
  rest of the V2 backlog are specced but unbuilt.

**To resume:** `git checkout v2`, then read this file → the [V2 spec](v2-design-spec.md) →
the design doc for whichever feature you're building next
([V2.1](v2.1-citizen-view-design.md) / [V2.2](v2.2-trip-mode-design.md)).

---

## Done — V2.0 visible loop (branch `v2`)

The dashboard is no longer a static mock; it's a live loop. Submit a photo → an in-process
background worker detects + clusters it → it appears on the dashboard with its **real photo**
→ a reviewer drives its lifecycle via `PATCH`.

Shipped:
- Pipeline DB layer: issue lifecycle transitions + validation + `issue_events` audit, evidence
  resolver, idempotent seeding (`pipeline/db.py`, `pipeline/models.py`).
- `GET /v1/issues` served from the live DB (mock retired as render source); seeds demo data on
  first run.
- In-process **background worker** (`pipeline/worker.py`) on the FastAPI lifespan: drains the
  report queue → process → 10m dedup, on a poll interval.
- `GET /v1/issues/{id}/evidence` — real photo, with `?w=` on-the-fly thumbnail (≈18× smaller)
  + immutable caching.
- `PATCH /v1/issues/{id}` — lifecycle-validated status/severity/note (the reviewer action).
- Dashboard rewired to live data + real photos + PATCH actions (design preserved).

Verification: **67 tests pass**, ruff lint+format clean; per-task + whole-branch reviews all
green; the full loop was confirmed live in a browser (submit real photo → worker → clustered
issue → dashboard render → PATCH). Implementation plan:
[`docs/superpowers/plans/2026-08-23-v2.0-visible-loop.md`](superpowers/plans/2026-08-23-v2.0-visible-loop.md).

---

## Next up (in suggested order)

1. **Open a PR** `v2` → `main` (V2.0). Not done yet — decide before stacking more on `v2`.
2. **V2.1 — Citizen-facing view** → [`docs/v2.1-citizen-view-design.md`](v2.1-citizen-view-design.md).
   Single portal for everyone; admin-only review controls. Gated by the privacy blur gate and
   (for "my reports") auth/RBAC.
3. **V2.2 — Trip / dashcam mode** → [`docs/v2.2-trip-mode-design.md`](v2.2-trip-mode-design.md).
   Record a trip; auto-tag potholes/garbage along the GPS track.
4. **Rest of the V2 backlog** → [`docs/v2-design-spec.md`](v2-design-spec.md): foreground-validation
   gate (§5), auto-review/scaling (§5b), admin model-selection UI (§5c), auth/RBAC (§5d),
   filing pipeline (§5e — CPGRAMS + Swachhata, realistically the heaviest track).

Build any feature with the same workflow used for V2.0: spec (already written) → implementation
plan (`superpowers:writing-plans`) → subagent-driven execution with per-task + whole-branch review.

---

## Locked decisions (do not re-litigate)

| Decision | Value | Why |
|---|---|---|
| Dedup radius | **10 m** | Product decision; distinct issues are ≥10 m apart. |
| Worker | **In-process** on the app lifespan (zero-infra) | Stand-in for Celery/Kafka; swappable later. |
| Default detector | **stub** (deterministic, offline) | Tests/demo need no model or network. VLM is opt-in. |
| VLM cloud model | **`gemini-3.6-flash`** (NOT `gemini-2.5-flash` — retired for new API users, returns 404) | Validated live; drop-in via the OpenAI-compat endpoint. |
| Coordinates | Stored **as-is**, geocoding deferred | Ward shows `—`; the ward filter is inert until geocoding lands. |
| Citizen view | **Single portal** for everyone; admin just gets the review controls | Simplest; role-gate review actions when auth exists. |
| Auth/RBAC | **Deferred** | Blocks the admin panel + any public/citizen deployment; its own foundational task. |
| Filing | **Human always presses send**; never auto-file | Core safety principle. |
| Trip mode tagging | **Batch, not live** (with a cloud VLM) | Cloud VLM latency (~25 s/img) rules out live tagging; on-device model needed for near-real-time. |

---

## Run & verify

Requires [uv](https://docs.astral.sh/uv/) and Python 3.14+.

```bash
uv sync
uv run trashtag                     # http://127.0.0.1:8000  (dashboard, /docs, /mcp)
uv run pytest -q                    # 67 tests, offline
uv run ruff check . && uv run ruff format --check src/ tests/
```

Detection providers (opt-in; default is `stub`):
```bash
# Local, free — Ollama
ollama serve && ollama pull qwen3-vl:2b
TRASHTAG_DETECTOR=vlm TRASHTAG_VLM_MODEL=qwen3-vl:2b uv run trashtag

# Cloud, free tier — Google AI Studio (Gemini). Key: GEMINI_API_KEY in .env.local (git-ignored).
TRASHTAG_DETECTOR=vlm \
TRASHTAG_VLM_HOST=generativelanguage.googleapis.com TRASHTAG_VLM_PORT=443 \
TRASHTAG_VLM_PATH=/v1beta/openai TRASHTAG_VLM_MODEL=gemini-3.6-flash \
TRASHTAG_VLM_API_KEY=$GEMINI_API_KEY uv run trashtag
```
Behind a TLS-intercepting corporate proxy, export system roots first:
`export SSL_CERT_FILE=/path/to/roots.pem` (see the VLM detector notes).

Worker knobs: `TRASHTAG_WORKER=on|off`, `TRASHTAG_WORKER_POLL_SECONDS` (default 5).

---

## Where the code lives

```
src/trashtag/
├── constants/   names, issue classes/statuses, OS-agnostic paths
├── helper/      runtime config + canonical mock seed data (mock_issue_rows)
├── app/         FastAPI service (serve.py: endpoints + worker lifespan + MCP), static/dashboard.html
└── pipeline/    models · geo · store · db · interfaces        (shared seam — ALL SQL lives in db.py)
                 ingest · detector · vlm · process · dedup · frames · worker   (stages)
```
Seam rule: **no SQL outside `pipeline/db.py`**. Detector is a `Detector` protocol; providers
swap via `TRASHTAG_DETECTOR` + `TRASHTAG_VLM_*` with no pipeline changes.

## Doc index
- [Architecture & build plan](civic-vision-architecture-plan.md) · [Dashboard design spec](civic-vision-dashboard-design-spec.md)
- [V2 design spec](v2-design-spec.md) · [V2.1 citizen view](v2.1-citizen-view-design.md) · [V2.2 trip mode](v2.2-trip-mode-design.md)
- Research: [Qwen/VLM detector](research/qwen2.5-vl-detector.md) · [India filing portal](research/india-filing-portal-recommendation.md) · [ICMC adapter](research/ichangemycity-filing-adapter.md)
