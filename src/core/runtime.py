# src/core/runtime.py
"""
Server Runtime Identity

Generates a single UUID4 at process import time that uniquely identifies
this specific server run. Every restart produces a new ID — the probability
of two runs sharing the same ID is statistically zero (2^122 possible values).

Usage:
    from src.core.runtime import RUNTIME_ID, RUNTIME_START

    logger.info(f"Runtime ID: {RUNTIME_ID}")
"""

import uuid
from datetime import datetime

# Generated once when the module is first imported — fixed for the entire
# lifetime of this process. A new server start = a new import = a new ID.
RUNTIME_ID: str = str(uuid.uuid4())

# ISO timestamp of when this runtime started (same moment as ID generation).
RUNTIME_START: datetime = datetime.now()


def get_runtime_info() -> dict:
    """Return a dict with runtime ID and start time for embedding in responses."""
    return {
        "runtime_id": RUNTIME_ID,
        "started_at": RUNTIME_START.isoformat(),
        "uptime_seconds": (datetime.now() - RUNTIME_START).total_seconds(),
    }
