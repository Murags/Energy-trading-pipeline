---
story_id: "7.2"
title: "Implement Fixed-Schedule Retraining Policy"
status: "review"
baseline_commit: fa808dc32f28caaf6690c179037d84d5ee3f44a2
parent_epic: "Epic 7: Retraining Strategies and Event Logging"
priority: "P0"
suggested_sprint: "Sprint 7"
source: "_bmad-output/epics.md"
---

# Story 7.2: Implement Fixed-Schedule Retraining Policy

## Status

review

## Parent Epic

Epic 7: Retraining Strategies and Event Logging

## Priority

P0

## Suggested Sprint

Sprint 7

## User Story

As a researcher, I want weekly fixed-schedule retraining so that scheduled retraining can be compared with performance-triggered retraining.

## Description

Implement `fixed_schedule` policy with configurable retraining interval and weekly default.

## Acceptance Criteria

Policy triggers at configured interval, default interval is weekly, training window details are passed to event logging, strategy identifier is `fixed_schedule`.

## Technical Notes

Use config values rather than hard-coded intervals where practical.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/retraining/fixed_schedule.py`, `configs/experiment.yaml`.

## Testing Requirements

Unit tests verify weekly and custom interval decisions.

## Tasks/Subtasks

- [x] Implement weekly and configurable fixed-schedule decisions using the Story 7.1 contract.
	- [x] Verify interval boundaries, repeated decisions, UTC handling, and invalid intervals.
	- [x] Load the interval from the existing experiment configuration.
- [x] Pass explicit training-window metadata to an event-logging callback without implementing the Story 7.4 event writer.
	- [x] Verify callback metadata and leakage-safe training-window boundaries.
- [x] Add focused integration coverage and run the regression and configured quality checks.

## Dependencies

Story 7.1.

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

- Workflow activation used the documented manual fallback because system `python3`
	lacks `tomllib`. No team/user overrides or project-context files were present.
- User approved adding the missing AC-derived Tasks/Subtasks section.
- No sprint-status file exists; progress is tracked in this story only.
- Story 7.1 is implemented and available with status `review`.
- Interval red phase: `uv run pytest tests/unit/test_retraining_policies.py` failed
	on the missing `FixedSchedulePolicy` import.
- Interval green phase: 27 policy unit tests passed; full regression: 765 passed.
- Editor diagnostics: no errors in the policy implementation or unit tests.
- Metadata red phase: seven callback tests failed on unsupported hook keyword
	arguments, with 28 existing tests passing.
- Metadata green phase: 35 policy unit tests passed; full regression: 773 passed.
- Final focused check: `uv run pytest tests/unit/test_retraining_policies.py
	tests/integration/test_backtest_runner_small_range.py` -> 57 passed.
- Task-completion regression gate: `uv run pytest` -> 779 passed.
- Story-completion regression gate after task completion: `uv run pytest` ->
	779 passed. All approved tasks/subtasks were re-scanned and are complete.
- `git diff --check` passed; editor diagnostics show no errors in the touched
	Python files. No separate linting/static-analysis command is configured in
	`pyproject.toml` or CI.

### Completion Notes

- Implemented the `fixed_schedule` boolean policy with a weekly default and an
	explicit `from_config` factory using `fixed_schedule_interval_days`.
- The first decision anchors the schedule; later positive decisions restart the
	interval at the actual decision timestamp. Repeated timestamps do not trigger twice.
- UTC elapsed days preserve fixed durations across DST changes. Invalid durations
	fail fast; inherited timestamp/history guards remain in effect.
- Optional hook callbacks forward the caller-supplied `TimeWindow` as UTC ISO
	bounds together with strategy, trigger reason, interval, and decision timestamp.
	Invalid or future windows fail before advancing the policy. No writer was added.
- The runner still raises
	`NotImplementedError` for positive decisions; implementing model lifecycle and
	the Story 7.4 event writer is not part of this story.
- Added 26 unit cases and three integration cases covering weekly/custom
	schedules, UTC/DST timing, repeated and late decisions, config loading, invalid
	inputs, unchanged forecast history, metadata handoff, and the runner boundary.
- README documents the policy API and callback example, including the static-only
	CLI and deferred refit execution. Existing weekly YAML configuration required
	no changes. No dependencies, generated datasets, or future story code were added.
- All acceptance criteria and approved tasks are verified. No story-scope blockers
	remain; full retraining execution and persisted event logs remain future work.
- Status is `review`. The original QA Checklist is unchanged under the workflow's
	story-edit restrictions; its conditions were validated and recorded above.

## File List

- `README.md` (modified)
- `src/energy_trading_pipeline/retraining/fixed_schedule.py` (modified)
- `tests/unit/test_retraining_policies.py` (modified)
- `tests/integration/test_backtest_runner_small_range.py` (modified)
- `_bmad-output/implementation-artifacts/sprint-7/story-7.2-implement-fixed-schedule-retraining-policy.md` (modified)

## Change Log

- 2026-10-05: Added the approved task sequence and implemented weekly/custom
	fixed-schedule decisions with configuration and interval-boundary tests;
	added explicit training-window event metadata handoff, fixture integration
	coverage, and usage documentation.
