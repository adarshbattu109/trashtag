"""All static constants for TrashTag."""

APP_NAME = "TrashTag"
TAGLINE = "Tag the trash. Flag the roads."
VERSION = "0.1.0"

# Detection classes. These map directly onto the dashboard's civic color tokens
# (pothole = hazard-yellow, garbage = waste-green).
ISSUE_CLASSES = ("pothole", "garbage")

# Issue lifecycle, per the architecture plan §2.3. "rejected" is a terminal off-ramp
# for false detections a reviewer throws out.
ISSUE_STATUSES = ("new", "verified", "filed", "in_progress", "resolved", "rejected")

# Where MCP is mounted on the FastAPI app.
MCP_MOUNT = "/mcp"
