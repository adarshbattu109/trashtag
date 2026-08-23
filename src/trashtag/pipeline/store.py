"""Filesystem media store — the zero-infra stand-in for S3/MinIO (architecture §2.1).

Used by both the ingestion stage (save) and the processing stage (open), so it lives in the
shared seam rather than either stage. Swap in an S3-backed store with the same two methods.
"""

from pathlib import Path

from trashtag.constants.filepaths import MEDIA_DIR


class FilesystemMediaStore:
    """Stores uploaded media as files under a root directory, keyed by an opaque relative path."""

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root is not None else MEDIA_DIR
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, name: str) -> str:
        """Write `data` under `name` and return the storage path (relative to root) to persist
        on the Report. `name` should be unique (e.g. include the report id) — the caller owns
        uniqueness; this store overwrites on collision."""
        # Guard against path traversal from a caller-influenced name.
        safe = Path(name).name
        (self.root / safe).write_bytes(data)
        return safe

    def open(self, path: str) -> bytes:
        """Read back the bytes previously saved at `path`. Raises FileNotFoundError if absent."""
        return (self.root / Path(path).name).read_bytes()
