---
story_id: "7.1"
title: "Define Retraining Policy Interface and No-Retraining Policy"
status: "review"
baseline_commit: b68143cc291a5a2b446081060e99577b2345101e
parent_epic: "Epic 7: Retraining Strategies and Event Logging"
priority: "P0"
suggested_sprint: "Sprint 7"
source: "_bmad-output/epics.md"
---

# Story 7.1: Define Retraining Policy Interface and No-Retraining Policy

## Status

review

## Parent Epic

Epic 7: Retraining Strategies and Event Logging

## Priority

P0

## Suggested Sprint

Sprint 7

## User Story

As a developer, I want a common retraining policy interface so that strategies can be swapped in the same backtest runner.

## Description

Implement base policy contract and no-retraining strategy.

## Acceptance Criteria

Policy interface returns retrain/no-retrain decisions, `no_retraining` trains once and never triggers retraining after initial model creation, strategy identifier is stable.

## Technical Notes

Do not hard-code strategy behavior into the backtest runner.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/retraining/policies.py`, `src/energy_trading_pipeline/retraining/no_retraining.py`.

## Testing Requirements

Unit test verifies no-retraining behavior across multiple decision timestamps.

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

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Implementation Plan

1. Add `RetrainingPolicy` abstract base class in `retraining/policies.py` holding the shared
   contract: a stable canonical `strategy` identifier, validated `should_retrain` entry point,
   abstract `_decide` for strategy logic, and `as_policy_hook()` adapting the policy to the
   existing `PolicyHook` signature in `backtesting/backtest_runner.py`.
2. Centralize leakage and input guards in the base class so strategy subclasses stay minimal:
   timezone-aware decision timestamps normalized to UTC, non-decreasing decision order,
   canonical forecast-log columns, deep-copied history, and rejection of any history record
   dated after the decision timestamp.
3. Add `NoRetrainingPolicy` in `retraining/no_retraining.py` returning False at every decision.
4. Cover the contract with unit tests and one fixture-sized integration test confirming the
   policy can be swapped into the existing backtest runner without runner changes.

### Debug Log

- Red phase: `uv run pytest tests/unit/test_retraining_policies.py` failed on import (no
  `NoRetrainingPolicy`), confirming the new tests exercise new code.
- Green phase: 12 unit tests pass after implementing `policies.py` and `no_retraining.py`.
- Regression: `uv run pytest` → 750 passed.

### Completion Notes

- Policy interface returns boolean retrain/no-retrain decisions and enforces a `bool` return
  from subclasses, matching the runner's existing hook contract (`policy_hook` returning bool).
- `no_retraining` never triggers retraining after initial model creation; verified across five
  successive decision timestamps with growing history, and end-to-end through `run_backtest`
  where the model is fitted exactly once.
- Strategy identifiers are validated against the canonical `STRATEGIES` set in
  `backtesting/forecast_log.py`, so no new identifier strings were introduced.
- No backtest-runner changes were made; strategy behavior stays out of the runner, as required
  by the story's technical notes. Fixed-schedule, rolling RMSE, and event logging remain
  untouched for Stories 7.2-7.4.

### File List

- `src/energy_trading_pipeline/retraining/policies.py` (modified)
- `src/energy_trading_pipeline/retraining/no_retraining.py` (modified)
- `tests/unit/test_retraining_policies.py` (added)
- `tests/integration/test_backtest_runner_small_range.py` (modified)
- `_bmad-output/implementation-artifacts/sprint-7/story-7.1-define-retraining-policy-interface-and-no-retraining-policy.md` (modified)

### Change Log

- 2026-10-05: Implemented the shared retraining policy interface and the `no_retraining`
  strategy, with unit tests for the contract and an integration test for runner swap-in.
