---
story_id: "1.5"
title: "Create Sample Experiment Configuration"
status: "review"
baseline_commit: "f5c770478c09a9f6fe0c5b0f897e3bd70ce25203"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
---

# Story 1.5: Create Sample Experiment Configuration

## Status

Review

## Parent Epic

Epic 1: Project Setup and Configuration Foundation

## Priority

P0

## Suggested Sprint

Sprint 1

## User Story

As a developer, I want sample experiment configuration files so that the local-first pipeline has clear defaults before data processing begins.

## Description

Create sample YAML configuration files for experiment settings, local paths, model parameters, and fixture-based tests.

## Acceptance Criteria

`configs/experiment.yaml`, `configs/local_paths.yaml`, and `configs/model_params.yaml` exist; test fixture config exists under `tests/fixtures/sample_config.yaml`; defaults include weekly fixed-schedule retraining; defaults include a 7-day rolling RMSE window; rolling RMSE threshold is configurable; local CSV/Parquet paths are represented; no credentials are required.

## Technical Notes

Config defaults should support fixture/debug runs and should not imply full 2020-2025 execution by default.

## Files / Modules Likely Affected

`configs/experiment.yaml`, `configs/local_paths.yaml`, `configs/model_params.yaml`, `tests/fixtures/sample_config.yaml`.

## Testing Requirements

Config loader tests validate all sample config files.

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

## QA Checklist

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Implementation Plan

- Add repository sample YAML files compatible with the existing configuration loader.
- Extend the fixture configuration with the same retraining defaults.
- Verify all samples through the loader and run the full test suite.

### Completion Notes

- Added fixture-oriented experiment defaults with weekly fixed-schedule retraining,
  a 7-day rolling RMSE window, and a configurable rolling RMSE threshold.
- Added local CSV and Parquet artifact paths without credentials.
- Added XGBoost model parameters and loader coverage for all sample configurations.
- Verified with `uv run pytest -q` (42 passed).

## File List

- `_bmad-output/implementation-artifacts/sprint-1/story-1.5-create-sample-experiment-configuration.md`
- `configs/experiment.yaml`
- `configs/local_paths.yaml`
- `configs/model_params.yaml`
- `tests/fixtures/sample_config.yaml`
- `tests/unit/test_config_loader.py`

## Change Log

- 2026-07-12: Created sample experiment, local-path, and model-parameter YAML
  configurations; updated the fixture configuration and loader tests.
