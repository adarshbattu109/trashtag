"""All filesystem paths for TrashTag. Relative and OS-agnostic (pathlib)."""

import os
from pathlib import Path

# Relative to the CWD so logs land next to wherever the operator runs the server.
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Pipeline data root (zero-infra slice): SQLite DB + uploaded media on the local filesystem.
# Env-overridable so tests can point at a tmp dir.
DATA_DIR = Path(os.getenv("TRASHTAG_DATA_DIR", "data"))
MEDIA_DIR = DATA_DIR / "media"
DB_PATH = Path(os.getenv("TRASHTAG_DB", str(DATA_DIR / "trashtag.db")))
