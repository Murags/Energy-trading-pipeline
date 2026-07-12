---
story_id: "1.4"
title: "Add Initial CLI Entry Point"
status: "Ready for Dev"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
baseline_commit: "c5a92afe194004a8e323f9f00ccfff7e81db0df5"
---

# Story 1.4: Add Initial CLI Entry Point

## Status

Review

## Parent Epic

Epic 1: Project Setup and Configuration Foundation

## Priority

P0

## Suggested Sprint

Sprint 1

## User Story

As a researcher, I want a CLI entry point so that pipeline stages can be run reproducibly from commands.

## Description

Add a minimal CLI that loads config, prints resolved run settings, creates a run ID, and prepares run artifact folders.

## Acceptance Criteria

CLI accepts `--config`, creates `run_YYYYMMDD_HHMMSS`, writes `run_metadata.yaml`, and exits successfully without requiring data files or credentials.

## Technical Notes

Do not implement ingestion, preprocessing, modelling, or backtesting in this story.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/utils/time.py`, `src/energy_trading_pipeline/utils/io.py`, `logs/runs/`.

## Testing Requirements

Unit or integration test invokes CLI against `tests/fixtures/sample_config.yaml`.

## Dependencies

Story 1.3.

## Tasks / Subtasks

- [x] Implement run ID helper in `utils/time.py` (AC: run ID creation)
  - [x] `generate_run_id()` returns a `run_YYYYMMDD_HHMMSS` identifier
  - [x] Unit tests cover format and injectable clock
- [x] Implement run artifact helpers in `utils/io.py` (AC: run folder + metadata)
  - [x] `create_run_directory()` creates `logs/runs/<run_id>/`
  - [x] `write_run_metadata()` writes `run_metadata.yaml` into the run directory
  - [x] Unit tests cover directory creation and metadata content
- [x] Implement `cli.py` entry point (AC: `--config`, prints resolved settings, exits successfully)
  - [x] Parse `--config` argument
  - [x] Load and validate config via `config.loader.load_config`
  - [x] Print resolved run settings
  - [x] Create run ID, run directory, and write `run_metadata.yaml`
  - [x] Return exit code 0 on success, without requiring data files or credentials
- [x] Add `tests/fixtures/sample_config.yaml` fixture for CLI testing (Testing Requirements)
- [x] Add integration test invoking the CLI against the fixture config
- [x] Run full regression suite and confirm no failures

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

- Read `_bmad-output/architecture.md` and `_bmad-output/epics.md` before implementation; confirmed Story 1.3 (config loader) is complete and available.
- Followed red-green-refactor per module: wrote failing unit tests for `utils/time.py`, `utils/io.py`, then a failing integration test for `cli.py`, then implemented each to green before moving to the next.
- Manually smoke-tested `uv run python -m energy_trading_pipeline.cli --config tests/fixtures/sample_config.yaml` against the real repo; confirmed console output, `logs/runs/run_<timestamp>/run_metadata.yaml` creation, and no data files or credentials required. Removed the generated run folder afterward (it is a runtime artifact, not a committed fixture).
- Ran `uv run pytest -q`: 41 passed (33 pre-existing + 8 new), no regressions.

### Completion Notes

- Implemented `src/energy_trading_pipeline/utils/time.py`: `generate_run_id()` formats a `run_YYYYMMDD_HHMMSS` identifier from an injectable `datetime`, defaulting to `datetime.now()`.
- Implemented `src/energy_trading_pipeline/utils/io.py`: `create_run_directory()` creates (idempotently) `logs/runs/<run_id>/`; `write_run_metadata()` writes a metadata dict as YAML to `run_metadata.yaml` inside that directory.
- Implemented `src/energy_trading_pipeline/cli.py`: `parse_args()`/`main()` parse a required `--config` argument, load and validate the experiment config via `config.loader.load_config` (no `local_paths`/`model_params` merging — out of scope for this story), print the run ID, config path, and resolved run settings, create the run directory, write `run_metadata.yaml` (containing `run_id`, `config_path`, and the resolved `config`), and return exit code `0`.
- Added `tests/fixtures/sample_config.yaml`: a minimal valid experiment config (all 8 required sections, valid date ordering) scoped strictly to this story's own Testing Requirements. `configs/experiment.yaml`, `configs/local_paths.yaml`, and `configs/model_params.yaml` remain out of scope — those are owned by Story 1.5 ("Create Sample Experiment Configuration"), per the precedent set in Story 1.3.
- Added unit tests for `utils/time.py` (format correctness, round-trip parsing, default-clock behavior) and `utils/io.py` (directory creation, idempotency, metadata YAML content), plus an integration test that invokes the CLI end-to-end against the fixture config and asserts the run directory, `run_metadata.yaml` contents, and console output, and a second test confirming `--config` is required.
- Added `logs/runs/run_*/` to `.gitignore` so CLI-generated run folders are never committed, while `logs/runs/.gitkeep` keeps the directory tracked.
- No new dependencies were added (PyYAML was already declared in Story 1.2).

## File List

- `src/energy_trading_pipeline/cli.py` (modified)
- `src/energy_trading_pipeline/utils/time.py` (modified)
- `src/energy_trading_pipeline/utils/io.py` (modified)
- `tests/unit/test_time_utils.py` (added)
- `tests/unit/test_io_utils.py` (added)
- `tests/integration/test_cli_entry_point.py` (added)
- `tests/fixtures/sample_config.yaml` (added)
- `.gitignore` (modified)

## Change Log

- 2026-07-12: Implemented Story 1.4 — added `generate_run_id`, `create_run_directory`/`write_run_metadata`, and a `cli.py` entry point that loads/validates config from `--config`, prints resolved run settings, creates a `run_YYYYMMDD_HHMMSS` run folder, and writes `run_metadata.yaml`, with unit and integration tests and a scoped `tests/fixtures/sample_config.yaml` fixture.
