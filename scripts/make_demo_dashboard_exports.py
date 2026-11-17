"""Write a SYNTHETIC dashboard export set for exercising the dashboard UI.

Nothing here comes from a model, a backtest, or market data. The spreads,
forecasts, errors, and retraining events are simulated so the dashboard can be
tested against a "healthy model" scenario: low error, a performance-triggered
strategy that retrains rarely, and a clear sawtooth in rolling RMSE.

The output never replaces the real exports. It goes to its own directory, and
every metrics row carries a ``synthetic_demo`` run_id so the dashboard labels
the view as synthetic. Do not cite these numbers as experiment results.

Usage:
    uv run python scripts/make_demo_dashboard_exports.py
    uv run python scripts/make_demo_dashboard_exports.py --output-dir /tmp/demo
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


RUN_ID = "synthetic_demo_not_experiment_results"
STRATEGIES = ("no_retraining", "fixed_schedule", "performance_triggered")
# Base model fits get distinct ids per strategy, mirroring the real exports.
BASE_VERSIONS = {
	"no_retraining": "model_20241231_120000",
	"fixed_schedule": "model_20241231_120100",
	"performance_triggered": "model_20241231_120200",
}
DECISION_HOUR_UTC = 17
WINDOW_HOURS = 7 * 24
MIN_PERIODS_HOURS = 6
THRESHOLD = 9.0
# Performance-triggered retrains only after this many consecutive daily
# decisions find rolling RMSE above the threshold, so a one-day excursion that
# recovers by itself never causes a refit.
CONSECUTIVE_BREACHES = 3
FIXED_INTERVAL_DAYS = 7
# Error scale (EUR/MWh) of a fresh model, the level it degrades towards, and
# how many days that degradation takes to close ~63% of the gap.
FRESH_SIGMA = 5.6
STALE_SIGMA = 12.5
DEGRADATION_DAYS = 75.0
# Market-shock episodes (e.g. outages, interconnector constraints) per year,
# their length in days, and the extra error they add. A model fitted after an
# episode starts has seen part of the new regime and keeps only a fraction of
# the extra error.
SHOCKS_PER_YEAR = 9
SHOCK_DAYS = (2, 14)
SHOCK_EXTRA_SIGMA = (2.5, 6.0)
REFIT_SHOCK_FRACTION = 0.35
MARKER_FILE = "SYNTHETIC_DEMO_DATA.md"


def _actual_spread(timestamps: pd.DatetimeIndex, rng: np.random.Generator) -> np.ndarray:
	"""Plausible DE-FR spread: daily and weekly shape, seasonality, AR noise, spikes."""
	hours = np.arange(len(timestamps))
	hour_of_day = timestamps.hour.to_numpy()
	day_of_week = timestamps.dayofweek.to_numpy()
	day_of_year = timestamps.dayofyear.to_numpy()
	daily = 9 * np.sin(2 * np.pi * (hour_of_day - 7) / 24) + 6 * np.sin(
		4 * np.pi * (hour_of_day - 3) / 24
	)
	weekly = np.where(day_of_week >= 5, -6.0, 2.0)
	seasonal = 8 * np.cos(2 * np.pi * (day_of_year - 15) / 365)
	noise = np.zeros(len(hours))
	shocks = rng.normal(0, 4.0, len(hours))
	for index in range(1, len(hours)):
		noise[index] = 0.93 * noise[index - 1] + shocks[index]
	spikes = np.where(rng.random(len(hours)) < 0.004, rng.normal(0, 45, len(hours)), 0)
	return np.round(12 + daily + weekly + seasonal + noise + spikes, 2)


def _sigma(hours_since_fit: np.ndarray) -> np.ndarray:
	days = hours_since_fit / 24
	return FRESH_SIGMA + (STALE_SIGMA - FRESH_SIGMA) * (
		1 - np.exp(-days / DEGRADATION_DAYS)
	)


def _shock_episodes(
	n_hours: int, rng: np.random.Generator
) -> list[tuple[int, int, float]]:
	"""Random (start_hour, end_hour, extra_sigma) shock episodes."""
	count = max(1, round(SHOCKS_PER_YEAR * n_hours / (365 * 24)))
	starts = np.sort(rng.integers(14 * 24, max(15 * 24, n_hours - 24), count))
	return [
		(
			int(start),
			int(min(n_hours, start + rng.integers(*SHOCK_DAYS) * 24)),
			float(rng.uniform(*SHOCK_EXTRA_SIGMA)),
		)
		for start in starts
	]


def _shock_sigma(
	hours: np.ndarray, fit_index: int, shocks: list[tuple[int, int, float]]
) -> np.ndarray:
	extra = np.zeros(len(hours))
	for start, end, amount in shocks:
		inside = (hours >= start) & (hours < end)
		extra[inside] += amount * (REFIT_SHOCK_FRACTION if fit_index > start else 1.0)
	return extra


def _simulate_strategy(
	strategy: str,
	timestamps: pd.DatetimeIndex,
	actual: np.ndarray,
	shared_noise: np.ndarray,
	shocks: list[tuple[int, int, float]],
) -> tuple[pd.DataFrame, list[dict]]:
	"""Simulate one strategy day by day so decisions only see past errors.

	Rolling RMSE at hour t uses errors up to t-1h (one hour of actual
	availability lag) from the model currently serving, over at most 7 days.
	A retraining decision at 17:00 UTC therefore never sees a future error, and
	a refit model takes over at the next delivery day. Performance-triggered
	refits need CONSECUTIVE_BREACHES daily breaches in a row.
	"""
	days = timestamps.normalize().unique()
	errors = np.empty(len(timestamps))
	rolling = np.full(len(timestamps), np.nan)
	versions = np.empty(len(timestamps), dtype=object)
	version = BASE_VERSIONS[strategy]
	fit_index = 0
	refits = 0
	breaches = 0
	events: list[dict] = []
	for day in days:
		hours = np.flatnonzero(timestamps.normalize() == day)
		since = hours - fit_index
		sigma = _sigma(since) + _shock_sigma(hours, fit_index, shocks)
		errors[hours] = sigma * shared_noise[hours]
		versions[hours] = version
		for hour in hours:
			start = max(fit_index, hour - WINDOW_HOURS)
			window = errors[start:hour]
			if len(window) >= MIN_PERIODS_HOURS:
				rolling[hour] = float(np.sqrt(np.mean(window**2)))
		decision_hour = hours[timestamps[hours].hour == DECISION_HOUR_UTC]
		next_day = hours[-1] + 1
		if not len(decision_hour) or next_day >= len(timestamps):
			continue
		decision = decision_hour[0]
		score = rolling[decision]
		retrain = False
		reason = None
		if strategy == "fixed_schedule":
			retrain = next_day - fit_index >= FIXED_INTERVAL_DAYS * 24
			reason = "fixed_schedule_interval_elapsed"
		elif strategy == "performance_triggered":
			breaches = breaches + 1 if np.isfinite(score) and score > THRESHOLD else 0
			retrain = breaches >= CONSECUTIVE_BREACHES
			reason = "rolling_rmse_exceeds_threshold"
		if retrain:
			refits += 1
			version = f"{BASE_VERSIONS[strategy]}_refit_{refits:03d}"
			fit_index = next_day
			breaches = 0
			events.append({
				"timestamp": timestamps[decision],
				"strategy": strategy,
				"trigger_reason": reason,
				"threshold": THRESHOLD if strategy == "performance_triggered" else np.nan,
				"rolling_rmse": score if strategy == "performance_triggered" else np.nan,
				"model_version": version,
			})
	forecasts = pd.DataFrame({
		"timestamp": timestamps,
		"prediction": np.round(actual + errors, 4),
		"actual": actual,
		"strategy": strategy,
		"model_version": versions.astype(str),
		"rolling_rmse": rolling,
	})
	return forecasts, events


def build_demo_exports(
	start: str = "2025-01-01", end: str = "2025-12-31", seed: int = 7
) -> dict[str, pd.DataFrame]:
	"""Return the four dashboard exports for a deterministic synthetic run."""
	rng = np.random.default_rng(seed)
	timestamps = pd.date_range(
		pd.Timestamp(start, tz="UTC"),
		pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23),
		freq="h",
	)
	actual = _actual_spread(timestamps, rng)
	# One shared standard-normal error path keeps strategies comparable: they
	# differ only in how stale their model is, not in luck.
	shared_noise = rng.standard_t(df=6, size=len(timestamps)) / np.sqrt(1.5)
	shocks = _shock_episodes(len(timestamps), rng)
	forecasts, events = [], []
	for strategy in STRATEGIES:
		frame, strategy_events = _simulate_strategy(
			strategy, timestamps, actual, shared_noise, shocks
		)
		forecasts.append(frame)
		events.extend(strategy_events)
	forecasts_frame = pd.concat(forecasts, ignore_index=True).sort_values(
		["timestamp", "strategy"], kind="stable"
	).reset_index(drop=True)
	events_frame = pd.DataFrame(
		events,
		columns=[
			"timestamp", "strategy", "trigger_reason", "threshold",
			"rolling_rmse", "model_version",
		],
	).sort_values(["timestamp", "strategy"], kind="stable").reset_index(drop=True)
	events_frame["timestamp"] = pd.to_datetime(events_frame["timestamp"], utc=True)

	evaluation_end = timestamps[-1] + pd.Timedelta(hours=1)
	days = (evaluation_end - timestamps[0]) / pd.Timedelta(days=1)
	metrics = []
	for strategy, rows in forecasts_frame.groupby("strategy", sort=True):
		error = rows["prediction"] - rows["actual"]
		count = int((events_frame["strategy"] == strategy).sum())
		metrics.append({
			"run_id": RUN_ID,
			"evaluation_start": timestamps[0],
			"evaluation_end": evaluation_end,
			"strategy": strategy,
			"rmse": float(np.sqrt(np.mean(error**2))),
			"mae": float(np.mean(np.abs(error))),
			"retraining_count": count,
			"retraining_frequency": count / days,
		})
	model_versions = pd.DataFrame({
		"model_version": sorted(forecasts_frame["model_version"].unique()),
		"model_type": "xgboost",
	})
	return {
		"forecasts": forecasts_frame,
		"metrics": pd.DataFrame(metrics),
		"retraining_events": events_frame,
		"model_versions": model_versions,
	}


def write_demo_exports(output_dir: Path, **kwargs) -> dict[str, pd.DataFrame]:
	"""Write the synthetic exports and a marker file explaining their origin."""
	frames = build_demo_exports(**kwargs)
	output_dir.mkdir(parents=True, exist_ok=True)
	for name, frame in frames.items():
		frame.to_parquet(output_dir / f"{name}.parquet", index=False)
	(output_dir / MARKER_FILE).write_text(
		"# Synthetic demo data\n\n"
		"These dashboard exports were generated by "
		"`scripts/make_demo_dashboard_exports.py` for testing the dashboard UI.\n"
		"They are simulated, not produced by any model or backtest, and must not "
		"be reported as experiment results.\n"
	)
	return frames


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	parser.add_argument(
		"--output-dir", type=Path, default=Path("reports/dashboard_exports_demo")
	)
	parser.add_argument("--start", default="2025-01-01")
	parser.add_argument("--end", default="2025-12-31")
	parser.add_argument("--seed", type=int, default=7)
	args = parser.parse_args()
	real = Path("reports/dashboard_exports").resolve()
	if args.output_dir.resolve() == real:
		parser.error("refusing to overwrite the real exports in reports/dashboard_exports")
	frames = write_demo_exports(
		args.output_dir, start=args.start, end=args.end, seed=args.seed
	)
	print(f"Wrote SYNTHETIC dashboard exports to {args.output_dir}")
	print(frames["metrics"][["strategy", "rmse", "mae", "retraining_count"]].to_string(
		index=False
	))


if __name__ == "__main__":
	main()
