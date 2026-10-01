---
story_id: "6.2"
title: "Implement Forecast Log Schema"
status: "review"
baseline_commit: "feb8de545d259386570c023cfc841f4985796576"
parent_epic: "Epic 6: Backtesting Engine and Forecast Logging"
priority: "P0"
suggested_sprint: "Sprint 6"
source: "_bmad-output/epics.md"
---

# Story 6.2: Implement Forecast Log Schema

## Status

review

## Parent Epic

Epic 6: Backtesting Engine and Forecast Logging

## Priority

P0

## Suggested Sprint

Sprint 6

## User Story

As a developer, I want a forecast log schema so that all strategies produce comparable prediction records.

## Description

Define forecast log writing for timestamp, target timestamp, prediction, actual, error, squared error, absolute error, strategy, and model version.

## Acceptance Criteria

Forecast logs use canonical column names, logs can be written/read as Parquet or CSV, errors are computed consistently, strategy and model version are required.

## Technical Notes

Use `forecast_timestamp` if needed in addition to canonical `timestamp` for target period clarity.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/backtesting/forecast_log.py`, `logs/runs/`.

## Testing Requirements

Unit tests verify error calculations and required columns.

## Dependencies

Story 6.1.

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

- [ ] Story scope matches the approved `epics.md` entry.
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests are added or updated.
- [ ] Tests pass on fixture/debug data where applicable.
- [ ] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [ ] No secrets, tokens, credentials, or large generated datasets were committed.
- [ ] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Completion Notes

- Implemented on 2026-10-01. Story 6.1's splitter implementation and verification
  record are available; its tests pass in the regression suite. No sprint-status
  file exists, so progress is tracked in this story.
- Added `build_forecast_log(df)`, `write_forecast_log(df, output_path)`, and
  `read_forecast_log(input_path)` in the existing backtesting schema module.
- The nine canonical columns are `timestamp` (target delivery period),
  `forecast_timestamp` (issuance), `prediction`, `actual`, `error`,
  `squared_error`, `absolute_error`, `strategy`, and `model_version`.
- Both timestamp columns require timezone-aware inputs, normalize to UTC, and
  retain stable target-time ordering. Issuance cannot follow the target. Shared
  targets across strategies and empty logs are supported.
- Errors are `actual - prediction`, its square, and its absolute value. Missing
  actuals retain missing errors; predictions must be finite real numbers. Actual
  availability remains an explicit caller responsibility, not inferred from the
  target delivery timestamp.
- Strategy values must use the three approved identifiers. Model versions must
  be nonblank strings. Float arithmetic prevents unsigned integer wraparound;
  non-finite inputs/results and missing required columns fail clearly.
- Writers validate before creating parent folders, omit dataframe indexes, and
  replace the caller-specified artifact. Readers validate all nine columns and
  stored error consistency. CSV preserves identifier strings and UTC offsets.
- API docstrings document schema, error sign, missing-value behavior, and usage
  with configured paths under `logs/runs/run_YYYYMMDD_HHMMSS/`.

### Verified Implementation Tasks

- [x] Define canonical schema, error arithmetic, and required identifier validation.
- [x] Support Parquet and CSV writing/reading using caller-supplied run paths.
- [x] Add fixture-sized unit tests for arithmetic, required columns, validation,
  missing actuals, empty logs, shared targets, and artifact round-trips.
- [x] Confirm all acceptance criteria and original QA checklist conditions.
- [x] Verify scope, naming, module boundaries, and absence of generated datasets,
  secrets, new dependencies, or adjacent feature work.

### Debug Log

- Red phase: `uv run pytest -q tests/unit/test_forecast_log.py` failed during
  collection because the forecast-log functions did not yet exist.
- Initial green phase: the same command passed **58 tests**.
- Final expanded regression run: `uv run pytest -q` passed **709 tests** in
  **6.89s**, including **67 new forecast-log tests** and the Story 6.1 tests.
- `git diff --check` passed. No lint/static-analysis tools are configured in
  `pyproject.toml` or CI; Black and Ruff are not installed. Formatting was
  inspected against the project's 88-column convention.
- No implementation blockers. Original requirements and QA checklist text are
  preserved; completed verification evidence is recorded here.

## File List

- `src/energy_trading_pipeline/backtesting/forecast_log.py` (modified)
- `tests/unit/test_forecast_log.py` (added)
- `_bmad-output/implementation-artifacts/sprint-6/story-6.2-implement-forecast-log-schema.md`
  (status, baseline, and implementation record)

## Change Log

- 2026-10-01: Implemented canonical forecast log construction and validated
  Parquet/CSV persistence; added 67 tests and marked Story 6.2 ready for review.
