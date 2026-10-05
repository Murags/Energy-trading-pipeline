---
story_id: "7.4"
title: "Implement Performance-Triggered Retraining and Event Logging"
status: "review"
baseline_commit: a86c87f04a2b09bc262ff4c17d44340db33145f3
parent_epic: "Epic 7: Retraining Strategies and Event Logging"
priority: "P0"
suggested_sprint: "Sprint 7"
source: "_bmad-output/epics.md"
---

# Story 7.4: Implement Performance-Triggered Retraining and Event Logging

## Status

review

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

## Tasks/Subtasks

- [x] Implement the configurable performance-triggered policy using the rolling RMSE monitor.
	- [x] Trigger strictly above the threshold; do not trigger at or below it or with insufficient history.
	- [x] Preserve the policy interface, chronological decisions, and leakage guards; never use PSI as a trigger.
	- [x] Test threshold boundaries, configuration, invalid inputs, and history preservation.
- [x] Implement retraining event logging and Parquet persistence.
	- [x] Record trigger reason, threshold, rolling RMSE, training window, model version, timestamp, and strategy through explicit inputs.
	- [x] Test the policy-to-event handoff, required fields, timestamp handling, and persisted artifacts.
- [x] Document usage and verify the acceptance criteria with focused tests, full offline regressions, and configured quality checks.

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

## Dev Agent Record

### Debug Log

- Workflow activated using the documented manual resolver fallback. No overrides,
	project-context files, or sprint-status file were found.
- User authorized adding the missing task checklist derived from the existing
	story requirements. This is a fresh implementation with no review follow-ups.
- Story 7.3 is implemented and available with status `review`.
- Policy red phase failed on the missing class import. Green phase passed 103
	policy/monitor cases. Expanded policy coverage and full offline regression:
	`uv run pytest` -> 870 passed. Editor diagnostics report no errors.
- Event red phase failed on the missing writer API. The first green check found
	a Parquet text-dtype mismatch; explicit pandas string columns fixed it and the
	same focused check passed 107 cases.
- Comprehensive focused policy, event, and monitor validation: 195 passed.
	Event-task full offline regression: 936 passed. `git diff --check` passed;
	editor diagnostics are clean. No standalone lint/typecheck is configured.
- Documentation-task full offline regression: `uv run pytest` -> 936 passed.
	`git diff --check` passed. All approved task/subtask checkboxes are complete.
- Story-completion gate after task re-scan: `uv run pytest -q` -> 936 passed.
	Final whitespace check passed; the File List matches all six changed files.

### Completion Notes

- Implementation approach: reuse the decision-time rolling RMSE monitor and the
	existing policy validation contract. Compare strictly against a configured
	threshold. Keep model execution separate from policy decisions and event writing.
- Implemented configurable strict-above-threshold decisions using Story 7.3's
	monitor, including warm-up, missing-error, window, and chronological guards.
	PSI is ignored; no cooldown or error-history reset was introduced.
- Added an optional three-callback request handoff with explicit training window
	and model-version context. Requests do not claim that a refit succeeded.
- Added a canonical eight-column event schema, UTC normalization, half-open
	training-window validation, strict performance-trigger audit validation,
	chronological ordering, stable empty schemas, and local Parquet persistence.
	The writer replaces a complete log and validates before creating directories.
- Added 32 policy cases and 66 event cases, including the policy-to-Parquet
	handoff, malformed inputs, callback failure propagation, and no future errors.
- No new dependencies, credentials, datasets, or actual run artifacts were added.
	The backtest runner and CLI remain unchanged; model refit execution is outside
	this story's policy/event-writer scope.
- README documents configuration, thresholds, monitor readiness, callback inputs,
	event columns, complete-log replacement, and the unchanged execution boundary.
	Existing configuration already supplies the required settings.
- The original QA Checklist is unchanged under the story-edit restrictions;
	its conditions are verified here. No acceptance criteria or future story scope
	were changed. No implementation blockers remain.
- Definition of done passed: all approved tasks are checked, every acceptance
	criterion is satisfied, the 98 added cases and full offline suite pass, editor
	diagnostics are clean, and documentation and the complete File List are present.
	Status is `review`; no sprint tracking is configured. No commits were made.

## File List

- `README.md` (modified)
- `src/energy_trading_pipeline/retraining/performance_triggered.py` (modified)
- `src/energy_trading_pipeline/retraining/events.py` (modified)
- `tests/unit/test_retraining_policies.py` (modified)
- `tests/unit/test_retraining_events.py` (added)
- `_bmad-output/implementation-artifacts/sprint-7/story-7.4-implement-performance-triggered-retraining-and-event-logging.md` (modified)

## Change Log

- 2026-10-05: Added the user-authorized task checklist and implemented the
	configurable performance-triggered policy, explicit request handoff, validated
	Parquet event writer, 98 unit cases, and usage documentation.
- 2026-10-05: Completed all approved tasks and acceptance-criteria validation;
	936 offline regression tests passed. Marked the story `review`.
