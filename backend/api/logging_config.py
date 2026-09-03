"""Shared logging setup for the FastAPI backend.

Gives every `backend.api.*` module a consistently formatted logger so pipeline
milestones (uploads, Supabase writes, job status transitions) and live subprocess
output (SAM 3 loading, diffusion steps) show up together in the uvicorn console as
they happen — not just a wall of text dumped after a multi-minute run finishes or
fails. See subprocess_utils.run_streaming for the live-output half of this.
"""

import logging
import sys

_CONFIGURED = False


def configure_logging(level: int = logging.INFO) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
    )

    root = logging.getLogger("e2m")
    root.setLevel(level)
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"e2m.{name}")
