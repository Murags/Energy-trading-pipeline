---
story_id: "6.4"
title: "Add Backtesting CLI Command"
status: "Ready for Dev"
parent_epic: "Epic 6: Backtesting Engine and Forecast Logging"
priority: "P0"
suggested_sprint: "Sprint 6"
source: "_bmad-output/epics.md"
---

# Story 6.4: Add Backtesting CLI Command

## Status

Ready for Dev

## Parent Epic

Epic 6: Backtesting Engine and Forecast Logging

## Priority

P0

## Suggested Sprint

Sprint 6

## User Story

As a researcher, I want a CLI command for backtesting so that historical experiments can be rerun from config.

## Description

Add CLI support to run a small or configured backtest and write run metadata, forecast logs, and backtest logs.

## Acceptance Criteria

CLI runs a small fixture backtest, writes outputs under `logs/runs/run_*`, accepts config path, and does not require dashboard, AWS, or external API credentials.

## Technical Notes

Full strategy comparison happens later; this command establishes execution path.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/backtesting/backtest_runner.py`.

## Testing Requirements

Integration test invokes CLI on fixture data.

## Dependencies

Story 6.3.

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
