"""Optional Open-Meteo API adapter interface."""

import logging
from dataclasses import dataclass


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenMeteoClient:
    """Expose optional Open-Meteo fetching without enabling it by default."""

    enabled: bool = False

    @property
    def is_configured(self) -> bool:
        """Return whether optional Open-Meteo fetching is enabled."""
        return self.enabled

    def fetch(self) -> None:
        """Skip an unconfigured fetch or identify the unimplemented API boundary."""
        if not self.is_configured:
            LOGGER.warning(
                "Open-Meteo API adapter is not configured; skipping API fetch. "
                "Use a local cached file instead."
            )
            return None

        raise NotImplementedError("Open-Meteo API fetching is not implemented")
