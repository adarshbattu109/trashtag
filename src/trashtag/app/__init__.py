"""Entry point: start the TrashTag server (ops dashboard + issue API + MCP)."""

import logging
from pathlib import Path

import uvicorn

from trashtag.constants.constants import APP_NAME
from trashtag.constants.filepaths import LOG_DIR
from trashtag.helper.config import HOST, PORT, RELOAD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    filename=Path(LOG_DIR, "trashtag.log"),
)

logger = logging.getLogger(__name__)


def main(host: str = HOST, port: int = PORT, reload: bool = RELOAD):
    """Start the FastAPI server.

    Args:
        host: Interface to bind. Defaults to loopback (see config.py).
        port: Port to bind. Defaults to 8000.
        reload: Auto-reload on code change. On in dev, off otherwise.
    """
    logger.info("Starting %s at %s:%s", APP_NAME, host, port)
    uvicorn.run("trashtag.app.serve:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
