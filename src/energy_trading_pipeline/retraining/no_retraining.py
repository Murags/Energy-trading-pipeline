"""No-retraining strategy: train once at the start and hold the model fixed."""

import pandas as pd

from energy_trading_pipeline.retraining.policies import RetrainingPolicy


class NoRetrainingPolicy(RetrainingPolicy):
    """Never trigger retraining after the initial model is created."""

    strategy = "no_retraining"

    def _decide(
        self, decision_timestamp: pd.Timestamp, forecast_history: pd.DataFrame
    ) -> bool:
        """Return False at every decision point regardless of observed errors."""
        return False
