"""The TrashTag FastAPI app: serves the ops dashboard and exposes issue data over both
HTTP and MCP (so an LLM agent can query the same detections a reviewer sees)."""

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi_mcp import FastApiMCP

from trashtag.constants.constants import (
    APP_NAME,
    ISSUE_CLASSES,
    ISSUE_STATUSES,
    TAGLINE,
    VERSION,
)
from trashtag.helper.helper import get_issue, list_issues
from trashtag.pipeline.ingest import router as ingest_router

logger = logging.getLogger(__name__)

# The dashboard lives beside this module (app/static/), resolved from __file__ so it is
# found regardless of the CWD the server is launched from.
STATIC_DIR = Path(__file__).parent / "static"
DASHBOARD_HTML = STATIC_DIR / "dashboard.html"

app = FastAPI(title=APP_NAME, description=TAGLINE, version=VERSION)


@app.get("/", include_in_schema=False)
def dashboard():
    """Serve the single-page ops review dashboard."""
    # no-cache: the dashboard is one file that changes often during a prototype; a stale
    # disk-cached copy would show an old build after an update. Revalidate every load.
    return FileResponse(DASHBOARD_HTML, headers={"Cache-Control": "no-cache"})


@app.get("/health", operation_id="health")
def health():
    """Liveness check."""
    return {"status": "ok", "app": APP_NAME, "version": VERSION}


@app.get("/v1/issues", operation_id="list_issues")
def read_issues(
    # "class" is a Python keyword, so the query param is aliased and the argument renamed.
    issue_class: str | None = Query(default=None, alias="class"),
    status: str | None = Query(default=None),
):
    """List detected issues, optionally filtered by class and/or status.

    Returns 422 on an unknown class or status rather than silently returning everything —
    a typo'd filter that quietly ignores itself is worse than a clear rejection.

    NOTE: this reads the mock helper.list_issues; the pipeline writes to db.issues. Wiring
    this endpoint to the pipeline DB is the next integration step.
    """
    if issue_class and issue_class not in ISSUE_CLASSES:
        raise HTTPException(
            422,
            f"Unknown class '{issue_class}'. Expected one of {list(ISSUE_CLASSES)}.",
        )
    if status and status not in ISSUE_STATUSES:
        raise HTTPException(
            422, f"Unknown status '{status}'. Expected one of {list(ISSUE_STATUSES)}."
        )
    issues = list_issues(issue_class=issue_class, status=status)
    return {"count": len(issues), "issues": issues}


@app.get("/v1/issues/{issue_id}", operation_id="get_issue")
def read_issue(issue_id: str):
    """Fetch a single issue by its detection ID (e.g. A-0442)."""
    issue = get_issue(issue_id)
    if issue is None:
        raise HTTPException(404, f"No issue with ID '{issue_id}'.")
    return issue


# §2.1 ingestion: citizen-report intake. POST /v1/reports stores media + enqueues for the
# processing pipeline. Included before the MCP mount so it's reflected as a tool too.
app.include_router(ingest_router)


# Expose the HTTP API as MCP tools at /mcp. FastApiMCP reflects the existing routes, so
# every operation_id above becomes a tool an LLM agent can call — no separate tool defs.
# mount_http() is the current transport; plain mount() is deprecated in mcp 1.29.
mcp = FastApiMCP(app)
mcp.mount_http()
