---
story_id: "1.4"
title: "Add Initial CLI Entry Point"
status: "Ready for Dev"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
---

# Story 1.4: Add Initial CLI Entry Point

## Status

Ready for Dev

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
