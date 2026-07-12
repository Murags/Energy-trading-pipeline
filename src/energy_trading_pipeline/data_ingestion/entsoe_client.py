"""Optional ENTSO-E API adapter interface."""

import logging
from dataclasses import dataclass


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntsoeClient:
    """Expose optional ENTSO-E fetching without requiring API access."""

    api_key: str | None = None

    @property
    def is_configured(self) -> bool:
        """Return whether a non-empty ENTSO-E API key is available."""
        return bool(self.api_key and self.api_key.strip())

    def fetch(self) -> None:
        """Skip an unconfigured fetch or identify the unimplemented API boundary."""
        if not self.is_configured:
            LOGGER.warning(
                "ENTSO-E API adapter is not configured; skipping API fetch. "
                "Use a local cached file instead."
            )
            return None

        raise NotImplementedError("ENTSO-E API fetching is not implemented")
