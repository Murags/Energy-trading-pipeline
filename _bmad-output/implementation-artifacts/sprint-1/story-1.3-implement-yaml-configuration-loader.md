---
story_id: "1.3"
title: "Implement YAML Configuration Loader"
status: "Ready for Dev"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
baseline_commit: "5f3216fd3920332c6e252a51119b0595ed03cb00"
---

# Story 1.3: Implement YAML Configuration Loader

## Status

Review

## Parent Epic

Epic 1: Project Setup and Configuration Foundation

## Priority

P0

## Suggested Sprint

Sprint 1

## User Story

As a developer, I want a config loader so that paths, date ranges, model parameters, and retraining settings are controlled outside code.

## Description

Implement config loading and schema validation for experiment, local paths, and model parameter YAML files.

## Acceptance Criteria

Loader reads YAML files, validates required top-level sections, merges path/model config into the experiment runtime config, fails clearly on missing required keys, supports configurable start/end dates and retraining defaults.

## Technical Notes

Required sections are `data`, `dates`, `features`, `model`, `backtest`, `retraining`, `evaluation`, and `artifacts`.

## Files / Modules Likely Affected

`configs/experiment.yaml`, `configs/local_paths.yaml`, `configs/model_params.yaml`, `src/energy_trading_pipeline/config/loader.py`, `src/energy_trading_pipeline/config/schema.py`, `src/energy_trading_pipeline/config/paths.py`.

## Testing Requirements

Unit tests for valid config, missing required section, invalid date order, and path resolution.

## Dependencies

Story 1.2.

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

### Debug Log

- Read `_bmad-output/architecture.md` and `_bmad-output/epics.md` before implementation; confirmed Story 1.2 (dependencies) is complete and PyYAML is already a core dependency.
- Ran `uv run pytest -q`: 32 passed (8 pre-existing + 24 new config tests), no regressions.

### Completion Notes

- Implemented `src/energy_trading_pipeline/config/schema.py`: `validate_experiment_config` checks the 8 required top-level sections (`data`, `dates`, `features`, `model`, `backtest`, `retraining`, `evaluation`, `artifacts`), validates that `dates.start_date`/`dates.end_date` are present and parseable, and raises `ConfigValidationError` with a clear message (naming the missing sections/keys) when validation fails, including on invalid date ordering.
- Implemented `src/energy_trading_pipeline/config/paths.py`: `resolve_path`/`resolve_paths_config` resolve relative path strings against a base directory into absolute `Path` objects; `get_default_base_dir` infers the repository root from the module location so callers can omit an explicit base dir.
- Implemented `src/energy_trading_pipeline/config/loader.py`: `load_yaml_file` reads a YAML file into a dict, raising `FileNotFoundError` for a missing file and `ValueError` if the top-level content isn't a mapping. `load_config` reads the experiment config, validates it via `schema.py`, and — when provided — merges a resolved `local_paths.yaml` under a new `paths` key and merges `model_params.yaml` content into `model.params`, matching the "merge path/model config into the experiment runtime config" acceptance criterion.
- Deliberately did not populate `configs/experiment.yaml`, `configs/local_paths.yaml`, or `configs/model_params.yaml` with production content: those files (and `tests/fixtures/sample_config.yaml`) are explicitly owned by Story 1.5 ("Create Sample Experiment Configuration"), which depends on this story. All loader/schema/paths tests use `tmp_path`-generated fixtures to avoid duplicating or conflicting with that story's scope.
- Added unit tests covering all four required categories: valid config load (`test_config_schema.py`, `test_config_loader.py`), missing required section (both single and multiple), invalid date order (including equal start/end date), and path resolution (`test_config_paths.py`, plus loader merge test), for 24 new tests total.
- No new dependencies were added (PyYAML was already declared in Story 1.2).

## File List

- `src/energy_trading_pipeline/config/schema.py` (modified)
- `src/energy_trading_pipeline/config/paths.py` (modified)
- `src/energy_trading_pipeline/config/loader.py` (modified)
- `tests/unit/test_config_schema.py` (added)
- `tests/unit/test_config_paths.py` (added)
- `tests/unit/test_config_loader.py` (added)

## Change Log

- 2026-07-12: Implemented Story 1.3 — added required-section and date-order schema validation, path resolution utilities, and a YAML config loader that merges local paths and model params into the experiment runtime config, with unit tests for valid config, missing sections, invalid date order, and path resolution.
