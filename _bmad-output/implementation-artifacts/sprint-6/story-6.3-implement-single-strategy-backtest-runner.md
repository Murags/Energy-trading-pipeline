---
story_id: "6.3"
title: "Implement Single-Strategy Backtest Runner"
status: "review"
baseline_commit: "9eb751fd801b147df8282e4ffdfb72cabaff3f35"
parent_epic: "Epic 6: Backtesting Engine and Forecast Logging"
priority: "P0"
suggested_sprint: "Sprint 6"
source: "_bmad-output/epics.md"
---

# Story 6.3: Implement Single-Strategy Backtest Runner

## Status

review

## Parent Epic

Epic 6: Backtesting Engine and Forecast Logging

## Priority

P0

## Suggested Sprint

Sprint 6

## User Story

As a researcher, I want to run a backtest for one strategy at a time so that the runner can be validated before strategy comparison.

## Description

Implement runner orchestration that trains or loads models, predicts over the evaluation timeline, and writes forecast logs for a supplied retraining policy hook.

## Acceptance Criteria

Runner executes on fixture feature data, records predictions and actuals, writes forecast logs, supports a static model baseline path, preserves chronological order.

## Technical Notes

Keep retraining policy internals minimal until Epic 7; use a placeholder no-retraining hook if needed.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/backtesting/backtest_runner.py`, `src/energy_trading_pipeline/backtesting/forecast_log.py`.

## Testing Requirements

Integration test runs a small backtest and verifies output columns and row order.

## Dependencies

Story 6.2.

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

## Dev Agent Record

### Completion Notes

- Implemented on 2026-10-01. Story 6.2's forecast logger is available and its
  tests pass. No sprint-status file exists; status is tracked here.
- Added `run_backtest` using the existing configurable half-open backtest windows,
  XGBoost wrapper, and forecast log builder/writer. It trains once on the first
  training interval or loads a saved static model, then predicts each evaluation
  block in chronological order. Newly fitted models are saved to the supplied
  model artifact path; forecast output supports Parquet and CSV.
- The caller supplies feature columns, model version, and artifact paths. Loaded
  models must match configured parameters, target, and ordered features, and
  require a caller-verified history/availability upper bound before evaluation.
- Leakage concern addressed before implementation: feature rows for later hours
  in a forecast block may contain information unavailable at issuance. Required
  `feature_available_at` and `actual_available_at` columns explicitly declare
  availability. Forecast features and training labels are checked at issuance;
  hooks only receive isolated snapshots of prior forecasts with available actuals.
  These availability annotations must be supplied accurately by the caller.
- The optional boolean policy hook defaults to the static baseline placeholder.
  A positive decision fails explicitly with `NotImplementedError`; actual
  retraining execution and policies remain Epic 7 work, as permitted by this story.
- Validation covers hourly coverage, duplicate/naive timestamps, predictor
  selection, missing fields, and finite training targets. Missing evaluation
  actuals retain missing errors. Caller data is not mutated.
- API usage and assumptions are documented in the runner docstring. CLI/run
  metadata orchestration remains Story 6.4; no command or config schema changed.
- All acceptance criteria verified with small synthetic fixture data. No new
  dependencies or generated artifacts in source directories. No external API,
  AWS, dashboard, Docker, strategy comparison, or full historical experiments.
- The story has no Tasks/Subtasks section. The original QA checklist is retained
  unchanged under the workflow's permitted-section edit rules; verification is
  recorded here. No implementation blockers remain.

### Debug Log

- RED: `uv run pytest tests/integration/test_backtest_runner_small_range.py -q`
  failed at import because `run_backtest` did not exist.
- GREEN: the same command passed all 9 initial test cases after implementation.
- Added six further cases for timestamp/availability validation, finite training
  labels, missing evaluation actuals, and loaded-model contract mismatches.
- Regression: `uv run pytest -q` — **724 passed** (including all 15 new cases).
- `git diff --check` passed. No lint/static-analysis tool is configured in
  `pyproject.toml`; formatting and typing were reviewed against the coding guide.
- The customization resolver could not run with system Python (older than 3.11).
  Its fallback files were read manually: defaults only, no team/user overrides,
  no project-context file, and no completion hook.

## File List

- `src/energy_trading_pipeline/backtesting/backtest_runner.py` — runner and API contract.
- `tests/integration/test_backtest_runner_small_range.py` — 15 fixture-based cases.
- `_bmad-output/implementation-artifacts/sprint-6/story-6.3-implement-single-strategy-backtest-runner.md` — status, baseline, implementation record.

## Change Log

- 2026-10-01: Implemented static single-strategy backtesting with explicit
  availability checks, saved-model loading, policy placeholder, forecast
  persistence, and fixture regression coverage. Marked ready for review.
