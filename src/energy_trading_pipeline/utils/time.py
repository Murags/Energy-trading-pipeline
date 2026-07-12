"""Run ID and timestamp helpers."""

from datetime import datetime

RUN_ID_FORMAT = "run_%Y%m%d_%H%M%S"


def generate_run_id(now: datetime | None = None) -> str:
    """Generate a run ID in the form `run_YYYYMMDD_HHMMSS`."""
    timestamp = now if now is not None else datetime.now()
    return timestamp.strftime(RUN_ID_FORMAT)
