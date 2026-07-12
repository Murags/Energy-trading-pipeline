---
story_id: "7.3"
title: "Implement Rolling RMSE Monitor"
status: "Ready for Dev"
parent_epic: "Epic 7: Retraining Strategies and Event Logging"
priority: "P0"
suggested_sprint: "Sprint 7"
source: "_bmad-output/epics.md"
---

# Story 7.3: Implement Rolling RMSE Monitor

## Status

Ready for Dev

## Parent Epic

Epic 7: Retraining Strategies and Event Logging

## Priority

P0

## Suggested Sprint

Sprint 7

## User Story

As a researcher, I want rolling RMSE calculated from available forecast errors so that performance deterioration can be detected.

## Description

Implement rolling RMSE calculation with configurable window and no future error leakage.

## Acceptance Criteria

Default window supports 7-day rolling RMSE, function uses only available historical errors at decision time, outputs `rolling_rmse`, insufficient history is handled explicitly.

## Technical Notes

This metric drives performance-triggered retraining and must be tested carefully.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/monitoring/rolling_rmse.py`, `src/energy_trading_pipeline/monitoring/metrics.py`.

## Testing Requirements

Unit tests verify rolling RMSE values and no future error usage.

## Dependencies

Story 7.2.

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
