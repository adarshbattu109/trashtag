# Getting off the `mcp<2` pin

_Researched 2026-08-23. TrashTag depends on `fastapi-mcp>=0.4.0`; our entire MCP surface is
`FastApiMCP(app); mcp.mount_http()` in `src/trashtag/app/serve.py` — reflect existing FastAPI
routes as MCP tools at `/mcp`._

## Current state

| Package | Latest | Released | Constraint on `mcp` |
|---|---|---|---|
| `fastapi-mcp` | **0.4.0** | 2025-07-28 | `mcp>=1.12.0`, **no upper bound** |
| `mcp` (SDK) | **2.0.0** | 2026-07-28 | — (tracks the 2026-07-28 MCP spec, now the stable line) |
| `fastmcp` | **3.4.7** | 2026 | tracks current MCP spec; built on the SDK |

- **What broke:** mcp 2.0 dropped the `description` arg from `Server.__init__`. fastapi-mcp 0.4.0 still
  passes it, so an installed wheel crashes on import against mcp 2.x. Its declared `mcp>=1.12.0` has no
  cap, so pip/uv will happily resolve mcp 2.x — hence our defensive `mcp<2` pin. (Sources:
  [PyPI fastapi-mcp](https://pypi.org/pypi/fastapi-mcp/json), [PyPI mcp](https://pypi.org/project/mcp/2.0.0/).)
- **Upstream status — stale + unfixed.** fastapi-mcp's last commit is **2025-08-10** (a README badge);
  last real release 0.4.0 on 2025-07-28. Over a year with no functional release.
  - [#321](https://github.com/tadata-org/fastapi_mcp/issues/321) (open, 2026-07-28) — the
    `Server.__init__` crash against mcp 2.0.
  - [#323](https://github.com/tadata-org/fastapi_mcp/issues/323) (open, 2026-08-03) — request for real
    mcp 2.x support; notes the crash-only fix "only prevents the crash," not v2 support.
  - Several PRs (#254, #282, #292, #294, #317) are referenced as addressing the crash; **none merged, no
    release cut.**

**Bottom line:** no fastapi-mcp version supports mcp 2.x today, and there's no sign one is imminent.

## Options

**A — Wait + track + ignore the major bump.** Keep `mcp<2`, tell Dependabot to ignore mcp major updates,
watch #323. Zero work now, but bets on a stale project (no release in 12+ months) and leaves us stuck on
mcp 1.x indefinitely — including any 1.x security/spec drift.

**B — Upgrade fastapi-mcp to an mcp-2.x-capable release.** Not possible: no such release exists. A merge
of an existing crash-fix PR would only stop the import crash, not deliver v2 support. Not actionable.

**C — Migrate to `fastmcp` (the standalone 3.x project).** Actively maintained, tracks the current MCP
spec, and has first-class FastAPI reflection — the same "mount existing routes as tools" model we use.
Our two-liner becomes roughly:

```python
mcp = FastMCP.from_fastapi(app=app)          # reflect routes → tools (one line)
mcp_app = mcp.http_app(path="/mcp")          # ASGI app for HTTP transport
# mount mcp_app on the FastAPI app; combine its lifespan with our existing worker lifespan
```

Caveat: fastmcp's http mount needs its `lifespan` wired in, and we already run a worker `lifespan` in
`serve.py` — combine them via `combine_lifespans`. Also add `fastapi` explicitly (fastmcp doesn't pull
it) — already a direct dep for us. **Effort: low-to-medium, ~1 file (`serve.py`) + dependency swap**,
plus verifying the reflected tool names/paths match what agents expect.
(Source: [fastmcp FastAPI integration](https://gofastmcp.com/integrations/fastapi).)

## Recommendation

**Go with C — migrate to `fastmcp`.** fastapi-mcp is effectively unmaintained and has no mcp-2.x path;
`fastmcp` is the actively maintained tool for exactly our use case (reflect a FastAPI app as MCP tools)
and is compatible with the current mcp 2.x spec. **Next action:** in `serve.py`, replace
`FastApiMCP(app); mcp.mount_http()` with `FastMCP.from_fastapi(app=app)` mounted via `http_app("/mcp")`
(combining lifespans), then swap `fastapi-mcp` + `mcp<2` for `fastmcp` in `pyproject.toml`.

_Stopgap if we can't touch code this cycle:_ do A (Dependabot `ignore` major on `mcp`) so the bot stops
proposing bumps, and schedule C. Don't leave the pin unmanaged — Dependabot will keep reopening it.

## How to verify (after C)

```bash
uv lock && uv sync            # resolves fastmcp + mcp 2.x, no <2 cap
uv run python -c "from trashtag.app.serve import app"   # imports clean (the old crash path)
uv run trashtag &             # start the server
curl -s localhost:8000/mcp    # /mcp responds; confirm expected tools are listed
```
Confirm the tool set exposed at `/mcp` still covers the same endpoints reviewers see in the dashboard.
