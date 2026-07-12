---
story_id: "1.5"
title: "Create Sample Experiment Configuration"
status: "Ready for Dev"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
---

# Story 1.5: Create Sample Experiment Configuration

## Status

Ready for Dev

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

- [ ] Story scope matches the approved `epics.md` entry.
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests are added or updated.
- [ ] Tests pass on fixture/debug data where applicable.
- [ ] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [ ] No secrets, tokens, credentials, or large generated datasets were committed.
- [ ] Documentation or configuration was updated if this story changes usage or commands.
