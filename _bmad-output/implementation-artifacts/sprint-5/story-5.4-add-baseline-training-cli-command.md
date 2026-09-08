---
story_id: "5.4"
title: "Add Baseline Training CLI Command"
status: "review"
baseline_commit: "f6af693"
parent_epic: "Epic 5: XGBoost Model Training and Model Registry"
priority: "P0"
suggested_sprint: "Sprint 5"
source: "_bmad-output/epics.md"
---

# Story 5.4: Add Baseline Training CLI Command

## Status

review

## Parent Epic

Epic 5: XGBoost Model Training and Model Registry

## Priority

P0

## Suggested Sprint

Sprint 5

## User Story

As a researcher, I want a CLI command for baseline training so that model creation is reproducible from config.

## Description

Add CLI support to load feature data, train the model, save artifacts, and write training metadata.

## Acceptance Criteria

Command runs on fixture feature data, writes model artifact and metadata, uses configured model parameters, fails clearly if feature dataset is missing.

## Technical Notes

Do not implement backtesting or retraining in this story.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/models/trainer.py`.

## Testing Requirements

Integration test invokes training CLI against fixture data.

## Dependencies

Story 5.3.

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

Add a thin `train` CLI dispatch with explicit companion configuration flags. Use
the existing chronological selector and XGBoost wrapper in `train_baseline`, score
held-out validation rows, persist through story 5.3's registry, and write run
provenance. Preserve the shipped config-only bootstrap command.

### Debug Log

- Red: all six initial integration cases failed because `train` was unrecognized.
- Green: `uv run pytest -q` passed all 498 tests, including nine new CLI cases.
- `git diff --check` and `uv run python -m energy_trading_pipeline.cli train --help`
  passed. No lint/static-analysis tool is configured.
- Focused correctness check identified late strategy validation; moved it before
  artifact writes and added missing/unknown-strategy regression coverage.

### Completion Notes

- Subprocess coverage verifies command execution, configured model parameters,
  training-only fit equivalence, held-out RMSE/MAE, model artifacts, and run metadata.
- Missing files, missing configuration, overlapping windows, and same-hour raw
  prices fail clearly. Timestamp normalization is explicitly UTC.
- Inline and companion config paths/parameters are supported. Resolved paths are
  serialized as strings in provenance; generated artifacts stay outside source.
- README documents invocation, paths, chronology, outputs, and single-writer
  registry/version-collision behavior. No new dependencies were added.
- Story 5.3 is available on the parent branch in PR #84. No backtesting or
  retraining is executed. No sprint-status file exists; this file tracks status.

## File List

- `README.md`
- `src/energy_trading_pipeline/cli.py`
- `src/energy_trading_pipeline/models/trainer.py`
- `tests/integration/test_training_cli.py`
- `_bmad-output/implementation-artifacts/sprint-5/story-5.4-add-baseline-training-cli-command.md`

## Change Log

- 2026-09-08: Implemented and verified baseline training CLI for issue #33;
  ready for review.
