---
story_id: "7.4"
title: "Implement Performance-Triggered Retraining and Event Logging"
status: "Ready for Dev"
parent_epic: "Epic 7: Retraining Strategies and Event Logging"
priority: "P0"
suggested_sprint: "Sprint 7"
source: "_bmad-output/epics.md"
---

# Story 7.4: Implement Performance-Triggered Retraining and Event Logging

## Status

Ready for Dev

## Parent Epic

Epic 7: Retraining Strategies and Event Logging

## Priority

P0

## Suggested Sprint

Sprint 7

## User Story

As a researcher, I want retraining triggered when rolling RMSE exceeds a threshold so that model updates are tied to observed degradation.

## Description

Implement `performance_triggered` policy and retraining event writer.

## Acceptance Criteria

Policy triggers when rolling RMSE exceeds configurable threshold, event log records trigger reason, threshold, rolling RMSE value, training window, model version, timestamp, and strategy; PSI is not used as trigger.

## Technical Notes

Threshold may initially be derived from validation-period performance but must remain configurable.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/retraining/performance_triggered.py`, `src/energy_trading_pipeline/retraining/events.py`, `logs/runs/*/retraining_events.parquet`.

## Testing Requirements

Unit tests for below-threshold, at-threshold, above-threshold, and insufficient-history behavior.

## Dependencies

Story 7.3.

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
