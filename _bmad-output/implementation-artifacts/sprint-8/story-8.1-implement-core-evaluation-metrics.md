---
story_id: "8.1"
title: "Implement Core Evaluation Metrics"
status: "review"
baseline_commit: a6c3223ae6dbd96b1d250a0ab67c2896af5a1561
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P0"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.1: Implement Core Evaluation Metrics

## Status

review

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P0

## Suggested Sprint

Sprint 8

## User Story

As a researcher, I want RMSE, MAE, and retraining frequency calculated by strategy so that the three strategies can be compared.

## Description

Implement metric functions and strategy-level aggregation from forecast logs and retraining events.

## Acceptance Criteria

RMSE, MAE, and retraining count/frequency are calculated for each strategy, metrics handle missing actuals consistently, outputs use canonical column names.

## Technical Notes

Optional directional accuracy can be added after core metrics pass.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/monitoring/metrics.py`, `src/energy_trading_pipeline/evaluation/strategy_comparison.py`.

## Testing Requirements

Unit tests verify metric calculations against known small arrays.

## Tasks/Subtasks

- [x] Implement reusable RMSE and MAE functions in the monitoring module.
	- [x] Use the same observed-actual mask, return NaN without scored observations, and fail clearly for malformed inputs.
	- [x] Test known small arrays, missing actuals, empty inputs, and invalid values.
- [x] Aggregate core metrics by strategy from canonical forecast and retraining event logs.
	- [x] Calculate RMSE, MAE, retraining count, and retraining frequency per elapsed day over an explicit half-open evaluation window.
	- [x] Preserve stable strategy identifiers, canonical column names, comparable timelines, and input immutability.
	- [x] Test fixture logs, event-window boundaries, missing actuals, zero events, and invalid inputs.
- [x] Document the metric contracts and verify all acceptance criteria.
	- [x] Run focused tests, full offline regressions, and available code-quality checks.
	- [x] Record changed files and validation results without implementing future stories.

## Dependencies

Story 7.4.

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

- Workflow activated with the documented manual resolver fallback. No workflow
	overrides, project-context file, or sprint-status file is present.
- User approved adding this task checklist from the existing acceptance criteria.
	Fresh implementation; Story 7.4 is implemented and available with status `review`.
- Initial worktree was clean. Baseline recorded before implementation.
- Scalar red phase: new tests failed on missing metric imports. Green phase:
	39 metric cases passed. Full offline regression: 975 passed. Editor diagnostics
	and `git diff --check` passed; no standalone lint/typecheck is configured.
- Aggregation red phase failed on its missing API; initial green phase passed
	75 focused cases. Expanded coverage exposed two failures converting all-NA
	object actuals. Explicit missing-data normalization fixed both; the same focused
	check then passed 98 cases (53 scalar, 45 aggregation).
- Aggregation-task full offline regression: `uv run pytest -q` -> 1034 passed.
	Editor diagnostics, whitespace, and touched-code line-length checks passed.
- Documentation-task focused validation: 98 passed. Full offline regression:
	1034 passed. All six changed files have clean editor diagnostics; whitespace
	checks passed. The File List matches the actual worktree changes.
- Completion gate after re-scanning approved tasks: `uv run pytest -q` ->
	1034 passed. Final whitespace validation passed. No sprint tracking is configured.

### Completion Notes

- Implementation plan: calculate scalar errors in monitoring; aggregate validated
	canonical logs in evaluation. Use a shared observed-actual mask and explicit
	UTC half-open evaluation bounds. Frequency is completed retraining events per
	elapsed day, independent of missing actuals. Event logs must represent completed
	retraining, not unexecuted policy requests or initial model training.
- Implemented RMSE and MAE with positional pairing, consistent missing-actual
	filtering, explicit invalid-input errors, and scaled arithmetic. All 53 scalar
	tests and existing offline regressions pass.
- Added in-memory strategy aggregation with stable canonical columns, typed empty
	results, shared actuals/timelines, duplicate guards, and explicit UTC evaluation
	bounds. Counts use event logs, never forecast model-version changes; frequency
	uses elapsed days even across daylight-saving changes or missing actuals.
- Added 98 unit cases covering known arrays, nullable data, numerical validation,
	all three strategy logs, event boundaries, empty windows/logs, immutability,
	comparison validity, schema validation, and daylight-saving duration.
- README documents scalar inputs, missing-data behavior, canonical aggregation,
	half-open bounds, shared timeline checks, and events-per-day units. No new
	dependencies, credentials, generated datasets, configuration values, or exports
	were added. Training, CLI, dashboard, AWS, and Docker remain unchanged.
- The original QA Checklist is unchanged under the story-edit restrictions;
	its conditions are verified here. All approved task/subtask checkboxes are now
	complete, all acceptance criteria pass, and no implementation blockers remain.
- Definition of done passed: required unit coverage, all offline regressions,
	available quality gates, scope boundaries, usage documentation, and the complete
	File List are verified. Story status is `review`; no commits were made.

## File List

- `README.md` (modified)
- `src/energy_trading_pipeline/monitoring/metrics.py` (modified)
- `src/energy_trading_pipeline/evaluation/strategy_comparison.py` (modified)
- `tests/unit/test_metrics.py` (added)
- `tests/unit/test_strategy_comparison.py` (added)
- `_bmad-output/implementation-artifacts/sprint-8/story-8.1-implement-core-evaluation-metrics.md` (modified)

## Change Log

- 2026-10-05: Added the user-approved task checklist and started Story 8.1.
- 2026-10-05: Implemented RMSE, MAE, bounded strategy aggregation, 98 unit cases,
  and usage documentation; completed all approved tasks with 1034 regressions passing.
- 2026-10-05: Passed the final definition-of-done gate and marked the story `review`.
