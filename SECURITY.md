# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in TrashTag, please report it responsibly:

1. **Do NOT open a public issue.**
2. Use [GitHub Private Vulnerability Reporting](https://github.com/adarshbattu109/trashtag/security/advisories/new) to submit a report.
3. Include: description, reproduction steps, impact assessment, and suggested fix (if any).

### Response Timeline

- **Acknowledgment:** Within 72 hours
- **Assessment:** Within 7 days
- **Fix/Disclosure:** Within 90 days (coordinated disclosure)

## Scope

TrashTag currently runs a local FastAPI server that serves the internal ops dashboard and a
read-only issue API (`/v1/issues`) over **hardcoded mock data** — it makes no outbound network
calls and touches no database, so there is no SSRF surface and no third party receives your
data. We take the following seriously:

- **The server binds loopback by default.** `main()` in `src/trashtag/app/__init__.py`
  defaults to `host="127.0.0.1"` via `TRASHTAG_HOST`, so the surface is limited to processes
  on your machine. Setting `TRASHTAG_HOST=0.0.0.0` hands the dashboard and API to everyone on
  your network — this is an internal ops tool, not a public service. Don't expose it without
  authentication in front.
- **No authentication and no rate limiting.** Every endpoint is open to anyone who can reach
  the port. That is acceptable only because the server binds loopback. Before deploying to a
  shared host, put auth and rate limiting in front of it.
- **`/mcp` is mounted and unauthenticated.** `FastApiMCP` exposes the read endpoints as Model
  Context Protocol tools on the same server, with the same open access. It reads the same mock
  data — no write tools exist.
- **The dashboard is a single self-contained file.** `src/trashtag/app/static/dashboard.html` is HTML +
  inline CSS + vanilla JS. It never renders untrusted data as HTML; keep any DOM insertion on
  `textContent`, not `innerHTML`. It loads webfonts from Google Fonts and otherwise makes no
  external calls.
- **Logging runs at `INFO`** to `logs/trashtag.log` (`logs/` is gitignored). Log lines include
  reverse-geocoded issue addresses; treat log files as containing location data and check them
  before attaching to an issue.
- **Supply chain** — dependencies are monitored via Dependabot and `pip-audit` in CI.

## Design commitments (for the wider platform)

TrashTag files civic complaints on citizens' behalf; some safeguards are non-negotiable design
rules rather than code that exists today (see `docs/civic-vision-architecture-plan.md` §5):

- **Human always presses send.** No filing adapter auto-submits a complaint to an authority;
  the system drafts, a person reviews and sends.
- **Face/licence-plate blurring is a hard gate** before any citizen photo is eligible for the
  public map — build it before public launch, not after.
- **No reporter identity** is ever exposed on the public map or in a filed complaint.
- **Contractor/tender matches are always worded as "probable match, verify against tender
  documents"** — never asserted as fact.

## Non-Goals

- TrashTag does not authenticate callers or rate-limit requests in this prototype. It is a
  local ops tool, not a multi-tenant API gateway.
- TrashTag does not guarantee AI detection accuracy. A human reviewer confirms every issue
  before it is filed; do not treat a raw detection as verified.
