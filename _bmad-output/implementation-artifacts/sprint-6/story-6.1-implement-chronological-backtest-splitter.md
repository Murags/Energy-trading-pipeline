---
story_id: "6.1"
title: "Implement Chronological Backtest Splitter"
status: "Ready for Dev"
parent_epic: "Epic 6: Backtesting Engine and Forecast Logging"
priority: "P0"
suggested_sprint: "Sprint 6"
source: "_bmad-output/epics.md"
---

# Story 6.1: Implement Chronological Backtest Splitter

## Status

Ready for Dev

## Parent Epic

Epic 6: Backtesting Engine and Forecast Logging

## Priority

P0

## Suggested Sprint

Sprint 6

## User Story

As a researcher, I want chronological backtest periods so that historical simulation respects time order.

## Description

Build utilities that generate train, validation, and forecast windows for a configured evaluation range.

## Acceptance Criteria

Windows are ordered chronologically, future timestamps are excluded from training, small debug ranges are supported, invalid windows fail clearly.

## Technical Notes

This splitter may be reused by model training and retraining logic.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/backtesting/splitter.py`.

## Testing Requirements

Unit tests for window generation and leakage boundary cases.

## Dependencies

Story 5.4.

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
