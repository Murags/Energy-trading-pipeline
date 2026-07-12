---
story_id: "2.2"
title: "Define Raw Artifact Cache Layout"
status: "review"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P0"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
baseline_commit: "05f8af7d35e6098c93288efaff9b1ce1cdefb40b"
---

# Story 2.2: Define Raw Artifact Cache Layout

## Status

Review

## Parent Epic

Epic 2: Local Data Loading and Artifact Handling

## Priority

P0

## Suggested Sprint

Sprint 2

## User Story

As a developer, I want a raw artifact cache layout so that downloaded and local raw inputs are traceable.

## Description

Implement helpers that resolve and create raw data paths for ENTSO-E prices, load, generation, and Open-Meteo weather.

## Acceptance Criteria

Raw artifact paths follow `data/raw/entsoe/...` and `data/raw/open_meteo/...`, helpers create missing directories, path decisions are config-driven, raw files are treated as immutable once cached.

## Technical Notes

This story creates storage conventions only; it does not fetch API data.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/data_ingestion/cache.py`, `src/energy_trading_pipeline/config/paths.py`, `data/raw/`.

## Testing Requirements

Unit tests verify path resolution and directory creation in a temporary test directory.

## Dependencies

Story 2.1.

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

- [x] Add config-driven raw cache root resolution.
- [x] Add helpers for the ENTSO-E prices/load/generation and Open-Meteo weather layout.
- [x] Enforce immutable cached-file writes.
- [x] Add unit tests for path resolution, directory creation, validation, and immutability.
- [x] Run the full fixture-based regression suite and configured code-quality checks.

## Dev Agent Record

### Implementation Plan

- Resolve the raw cache root through the existing flat local-paths configuration boundary.
- Keep source/category layout rules in data ingestion and create directories on demand.
- Use exclusive file creation to prevent mutation of an already cached raw artifact.

### Debug Log

- Confirmed the focused test initially failed during collection because the raw-data resolver did not exist.
- Used `UV_CACHE_DIR=/tmp/energy-trading-pipeline-uv-cache` because the default uv cache is outside the workspace sandbox.

### Completion Notes

- Added config-driven resolution for the required `data_raw_dir` setting.
- Added helpers that create the ENTSO-E prices/load/generation and Open-Meteo weather directories and resolve validated artifact filenames.
- Added exclusive binary writes so an existing cached raw artifact raises `FileExistsError` and remains unchanged.
- Full regression suite passed: 58 tests. Compilation and whitespace validation also passed.

## File List

- `_bmad-output/implementation-artifacts/sprint-2/story-2.2-define-raw-artifact-cache-layout.md`
- `configs/local_paths.yaml`
- `src/energy_trading_pipeline/config/paths.py`
- `src/energy_trading_pipeline/data_ingestion/cache.py`
- `tests/unit/test_raw_cache.py`

## Change Log

- 2026-07-12: Defined the config-driven immutable raw artifact cache layout with unit coverage; status set to review.

## QA Checklist

- [ ] Story scope matches the approved `epics.md` entry.
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests are added or updated.
- [ ] Tests pass on fixture/debug data where applicable.
- [ ] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [ ] No secrets, tokens, credentials, or large generated datasets were committed.
- [ ] Documentation or configuration was updated if this story changes usage or commands.
