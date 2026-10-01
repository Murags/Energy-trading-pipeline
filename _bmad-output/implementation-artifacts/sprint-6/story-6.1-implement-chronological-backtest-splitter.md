---
story_id: "6.1"
title: "Implement Chronological Backtest Splitter"
status: "review"
parent_epic: "Epic 6: Backtesting Engine and Forecast Logging"
priority: "P0"
suggested_sprint: "Sprint 6"
source: "_bmad-output/epics.md"
---

# Story 6.1: Implement Chronological Backtest Splitter

## Status

review

## Parent Epic

Epic 6: Backtesting Engine and Forecast Logging

## Priority

P0

## Suggested Sprint

Sprint 6

## User Story

As a researcher, I want chronological backtest periods so that historical simulation respects time order.

## Description

Build utilities that generate train, validation, and forecast windows for a configured evaluation range.

## Acceptance Criteria

Windows are ordered chronologically, future timestamps are excluded from training, small debug ranges are supported, invalid windows fail clearly.

## Technical Notes

This splitter may be reused by model training and retraining logic.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/backtesting/splitter.py`.

## Testing Requirements

Unit tests for window generation and leakage boundary cases.

## Dependencies

Story 5.4.

## Implementation Notes

- Implement only the scope described in this story.
- Preserve the architecture boundaries defined in `_bmad-output/architecture.md`.
- Do not add adjacent features, dashboard work, AWS work, Docker work, or modelling work unless this story explicitly calls for it.
- Keep reusable project logic under `src/energy_trading_pipeline/` unless the story targets configuration, tests, docs, infrastructure, or repository metadata.
- Use `snake_case` for Python modules, functions, variables, dataframe columns, and artifact identifiers.

## Dev Agent Instructions

- Read `_bmad-output/architecture.md` and `_bmad-output/epics.md` before implementation.
- Confirm dependencies listed above are completed or available before starting.
- Make the smallest correct implementation that satisfies the acceptance criteria.
- Add or update tests listed in the testing requirements.
- Do not require external credentials unless the story explicitly concerns optional external integration.
- Do not run full 2020-2025 experiments for story verification unless explicitly required.

## QA Checklist

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Implementation and Verification Record

Implemented on 2026-10-01 against approved
`_bmad-output/implementation-artifacts/spec-6-1-chronological-backtest-splitter.md`,
baseline `636c30baa455e23c6573fb4a77dac79ba181166d`.

### API and Window Semantics

- Added frozen `TimeWindow(start, end)` and `BacktestWindow(train, validation, forecast)`
  dataclasses with interval and chronology validation. Endpoints are UTC-aware pandas
  timestamps, represented at nanosecond resolution, with half-open `[start, end)` bounds.
- Added `generate_backtest_windows(start_date, end_date, train_window_days,
  forecast_horizon_hours, *, validation_window_days)` returning an eager list.
  Calendar dates are inclusive inputs; strings must be strict `YYYY-MM-DD` and
  date objects are accepted, while datetime/timestamp values are rejected.
- For forecast start `t`, validation is `[t - validation_duration, t)` and training
  immediately precedes it for the configured training duration. Forecasts advance
  by the horizon and the final block is clipped at midnight after the end date.
- Added `generate_backtest_windows_from_config(config)` requiring five explicit
  `backtest` settings. Missing/malformed dates, durations, mappings, reversed
  bounds, and unrepresentable timestamp arithmetic fail with `ValueError`.
- Sample configurations evaluate January 6–8, 2023, with three training days,
  one validation day, and a 24-hour horizon. Baseline `dates` settings and model
  code remain unchanged. Story 5.4 implementation is available and its training
  CLI regression tests pass.

### Files Changed

- `src/energy_trading_pipeline/backtesting/splitter.py`
- `configs/experiment.yaml`
- `tests/fixtures/sample_config.yaml`
- `tests/unit/test_backtest_splitter.py` (new)
- `_bmad-output/implementation-artifacts/sprint-6/story-6.1-implement-chronological-backtest-splitter.md`
- `_bmad-output/implementation-artifacts/spec-6-1-chronological-backtest-splitter.md`
  (execution checkboxes and verification record only; frozen intent preserved)

### Tests Added and Acceptance Evidence

- Independently constructed standard-library hourly timestamps verify exact
  training, validation, and forecast row membership for daily and subdaily windows.
  Boundary probes include the instant before a boundary, exact shared endpoints,
  and the evaluation-exclusive end; validation and forecast targets are excluded
  from the same block's training interval.
- Forecast hours are covered exactly once, in order, for horizons of 1, 5, 24,
  25, 48, 72, and 100 hours, including clipped and oversized final blocks.
- One-day debug ranges require no datasets or credentials and cover leap day,
  year rollover, and both European DST-transition dates as 24-hour UTC days.
- Tests cover deterministic generation, immutable windows, calendar date objects,
  config equivalence and non-mutation, every missing setting, malformed calendar
  dates, datetime rejection, invalid durations, empty/inverted/overlapping intervals,
  timestamp/duration limits, historical underflow, and wide evaluation ranges.

### Verification Results

- `uv run pytest -q tests/unit/test_backtest_splitter.py tests/unit/test_training_window.py tests/unit/test_config_loader.py tests/integration/test_training_cli.py`
  — **176 passed in 3.09s** (final focused run).
- `uv run pytest -q` — **639 passed in 6.05s**.
- `git diff --check` — passed, no whitespace errors.

### Notes and Review Handoff

- Acceptance criteria are met; original story is ready for parent review.
  The approved spec remains `in-progress` pending that review.
- Rolling candidate windows do not prescribe retraining. Earlier evaluation
  observations may enter later history; market publication timing and feature
  availability at issuance still require separate runner validation.
- No new dependencies, model changes, commits, or remote operations. No generated
  experiment artifacts were added. No sprint-status file exists to synchronize.
- No implementation blockers. Parent agent owns the subsequent review step.

### Completed Review

- Blind, edge-case, and acceptance review passes completed; no acceptance violations.
- Fixed pandas 3 accepting second-resolution durations beyond nanosecond limits:
  durations now normalize during validation and raise field-specific `ValueError`.
  Three regression cases cover training, validation, and horizon durations.
- Final `uv run pytest -q`: **642 passed in 6.43s**. `git diff --check` passed.
- All accepted findings resolved. Approved spec is `done` and includes a suggested
  review order; original story stays `review` for human review. No blockers.
