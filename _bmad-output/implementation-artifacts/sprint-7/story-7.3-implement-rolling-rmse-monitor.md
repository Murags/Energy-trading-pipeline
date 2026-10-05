---
story_id: "7.3"
title: "Implement Rolling RMSE Monitor"
status: "review"
baseline_commit: 7eed124d088ff38eec87f903c9b7d6d04c6ad1c3
parent_epic: "Epic 7: Retraining Strategies and Event Logging"
priority: "P0"
suggested_sprint: "Sprint 7"
source: "_bmad-output/epics.md"
---

# Story 7.3: Implement Rolling RMSE Monitor

## Status

review

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

## Tasks/Subtasks

- [x] Implement a configurable rolling RMSE monitor over available forecast errors.
	- [x] Support the configured seven-day default and output `rolling_rmse`.
	- [x] Use only errors available at the decision timestamp within the rolling window.
	- [x] Handle insufficient history explicitly and validate required inputs.
- [x] Add unit tests for RMSE values, window boundaries, and no future error usage.
	- [x] Cover configuration, missing errors, timestamp handling, and input preservation.
- [x] Document the monitor contract and run focused tests, regression tests, and configured quality checks.

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

## Dev Agent Record

### Debug Log

- Workflow activation used the documented manual fallback because system
	`python3` lacks `tomllib`. No overrides, project-context files, or sprint-status
	file exist; progress is tracked in this story only.
- User authorized adding the missing AC-derived Tasks/Subtasks section.
- Story 7.2 is implemented and available with status `review`. This is a fresh
	implementation with no review follow-ups.
- Red phase: `uv run pytest tests/unit/test_rolling_rmse.py` failed on the missing
	`calculate_rolling_rmse` import.
- Green phase: 49 focused tests passed. Removed the observed pandas deprecation
	warning; the same 49 tests passed without warnings.
- Implementation-task regression gate: `uv run pytest` -> 828 passed.
- Editor diagnostics: no errors in the monitor or its unit tests.
- Comprehensive test task: 59 focused cases passed, including expired history,
	default readiness with unavailable actuals, nullable errors, numeric stability,
	excessive durations, and future-row strategy, duplicate, and dtype isolation.
- Test-task regression gate: `uv run pytest` -> 838 passed.
- `git diff --check` passed. No standalone lint or typecheck command is configured
	in `pyproject.toml` or CI; editor diagnostics remain clean.
- Final neighboring-contract check: `uv run pytest tests/unit/test_rolling_rmse.py
	tests/unit/test_retraining_policies.py tests/unit/test_forecast_log.py` ->
	164 passed.
- Documentation-task regression gate: `uv run pytest` -> 838 passed.
- Story-completion gate after re-scanning all approved task checkboxes:
	`uv run pytest` -> 838 passed. Final `git diff --check` passed.

### Completion Notes

- Implementation approach: calculate a named decision-time metric from a single
	strategy's observed errors in `(decision - window_days, decision]`, normalized
	to UTC. Filter target and optional issuance times before evaluating errors.
- Default readiness requires `window_days * 24` available hourly errors; missing
	values do not count and insufficient history returns `rolling_rmse: NaN`.
	`min_periods` can be supplied explicitly for small/debug histories.
- Input stays unchanged; duplicate targets and mixed strategies in the observed
	window fail clearly. Model-version changes do not reset available history.
- The existing canonical forecast log contract requires callers to leave errors
	missing until actuals become observable. No publication time is inferred.
- Only the rolling monitor is implemented; the evaluation metrics module,
	performance-triggered policy, runner lifecycle, and event writer are untouched.
- Added 59 unit cases using small in-memory canonical forecast logs and the
	existing experiment config. All acceptance criteria and approved tasks pass.
- README documents usage, UTC window boundaries, readiness, and the caller's
	responsibility for actual/error availability. Existing configuration needed
	no changes. No dependencies or generated datasets were added.
- The original QA Checklist is unchanged under the story-edit restrictions;
	its conditions were validated and recorded here. There are no scope blockers.
- Definition of done passed: all approved tasks are checked, all ACs are met,
	tests and configured quality checks pass, and the complete File List is below.
	Status is `review`; no sprint tracking is configured. No commits were made.

## File List

- `README.md` (modified)
- `src/energy_trading_pipeline/monitoring/rolling_rmse.py` (modified)
- `tests/unit/test_rolling_rmse.py` (added)
- `_bmad-output/implementation-artifacts/sprint-7/story-7.3-implement-rolling-rmse-monitor.md` (modified)

## Change Log

- 2026-10-05: Added the authorized task sequence and implemented decision-time
	rolling RMSE with configurable windows, explicit warm-up handling, leakage
	guards, 59 red-green unit cases, and usage documentation. Verified all approved
	tasks, acceptance criteria, neighboring contracts, and offline regressions.
