---
story_id: "5.2"
title: "Implement Training Window Selection"
status: "Ready for Dev"
parent_epic: "Epic 5: XGBoost Model Training and Model Registry"
priority: "P0"
suggested_sprint: "Sprint 5"
source: "_bmad-output/epics.md"
---

# Story 5.2: Implement Training Window Selection

## Status

Ready for Dev

## Parent Epic

Epic 5: XGBoost Model Training and Model Registry

## Priority

P0

## Suggested Sprint

Sprint 5

## User Story

As a researcher, I want chronological training windows so that model fitting avoids future data leakage.

## Description

Implement training dataset selection by configured train/validation date ranges and reusable window parameters.

## Acceptance Criteria

Training rows precede validation/evaluation rows, date ranges are config-driven, invalid overlapping ranges fail clearly, selected feature/target arrays are returned consistently.

## Technical Notes

This supports later backtesting and retraining windows.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/models/trainer.py`, `src/energy_trading_pipeline/backtesting/splitter.py` if shared.

## Testing Requirements

Unit tests for valid chronological split and invalid overlapping split.

## Dependencies

Story 5.1.

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
