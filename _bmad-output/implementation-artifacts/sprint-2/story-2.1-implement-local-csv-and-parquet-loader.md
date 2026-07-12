---
story_id: "2.1"
title: "Implement Local CSV and Parquet Loader"
status: "review"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P0"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
baseline_commit: "180d5bba778831655f8e55ff2e5c19853e8d4d03"
---

# Story 2.1: Implement Local CSV and Parquet Loader

## Status

Review

## Parent Epic

Epic 2: Local Data Loading and Artifact Handling

## Priority

P0

## Suggested Sprint

Sprint 2

## User Story

As a researcher, I want to load local CSV/Parquet files so that experiments can run without API access.

## Description

Implement reusable local loading functions for configured dataset paths and supported file formats.

## Acceptance Criteria

Loader reads CSV and Parquet, returns pandas DataFrames, validates file existence, logs source path and row count, raises clear errors for unsupported formats.

## Technical Notes

Keep local loading independent of ENTSO-E/Open-Meteo clients.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/data_ingestion/local_loader.py`, `src/energy_trading_pipeline/utils/io.py`.

## Testing Requirements

Unit tests load sample CSV and sample Parquet fixture data.

## Dependencies

Story 1.3.

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

## Tasks / Subtasks

- [x] Add a reusable local loader for configured CSV and Parquet dataset paths.
- [x] Validate file existence and raise a clear error for unsupported formats.
- [x] Log the loaded source path and row count.
- [x] Add unit tests for sample CSV and Parquet data, including error paths.
- [x] Run the full fixture-based regression suite.

## QA Checklist

- [ ] Story scope matches the approved `epics.md` entry.
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests are added or updated.
- [ ] Tests pass on fixture/debug data where applicable.
- [ ] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [ ] No secrets, tokens, credentials, or large generated datasets were committed.
- [ ] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Implementation Plan

- Add a focused `load_local_data` function in the data-ingestion boundary.
- Dispatch by file suffix, validate the supplied path, and log successful loads.
- Verify CSV and Parquet behavior with isolated temporary fixture data.

### Debug Log

- Confirmed the initial focused test run failed during collection because `load_local_data` did not exist.
- Used `UV_CACHE_DIR=/tmp/energy-trading-pipeline-uv-cache` because the default uv cache is outside the workspace sandbox.

### Completion Notes

- Implemented `load_local_data` for `.csv` and `.parquet` files using pandas.
- Added clear `FileNotFoundError` and `ValueError` paths for missing files and unsupported formats.
- Successful loads emit an INFO log with the source path and row count.
- Full regression suite passed: 46 tests.

## File List

- `_bmad-output/implementation-artifacts/sprint-2/story-2.1-implement-local-csv-and-parquet-loader.md`
- `src/energy_trading_pipeline/data_ingestion/local_loader.py`
- `tests/unit/test_local_loader.py`

## Change Log

- 2026-07-12: Implemented local CSV and Parquet loading with unit coverage; status set to review.
