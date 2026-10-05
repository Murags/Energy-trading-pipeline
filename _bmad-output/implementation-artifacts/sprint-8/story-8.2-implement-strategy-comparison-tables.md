---
story_id: "8.2"
title: "Implement Strategy Comparison Tables"
status: "review"
baseline_commit: e5a2c2ffd60258f32f980240205d9491447efef2
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P0"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.2: Implement Strategy Comparison Tables

## Status

review

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P0

## Suggested Sprint

Sprint 8

## User Story

As a researcher, I want strategy comparison tables so that results can be used in the final report.

## Description

Generate summary tables for RMSE, MAE, retraining count, retraining frequency, and optional directional accuracy.

## Acceptance Criteria

Tables are written under `reports/tables/`, strategy identifiers are stable, tables include run ID and evaluation period, output can be read by dashboard later.

## Technical Notes

CSV exports are acceptable for report readability; Parquet can be used for canonical dashboard exports.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/evaluation/strategy_comparison.py`, `reports/tables/`.

## Testing Requirements

Integration test builds comparison table from fixture forecast/event logs.

## Tasks/Subtasks

- [x] Build comparison tables from canonical forecast and completed-retraining logs.
	- [x] Reuse Story 8.1 metrics and preserve stable strategy identifiers.
	- [x] Include run ID and explicit UTC half-open evaluation bounds without mutating inputs.
	- [x] Add unit tests for values, metadata, empty inputs, and validation.
- [x] Persist report-readable and dashboard-readable comparison tables.
	- [x] Write run-scoped CSV and Parquet tables under the configured reports/tables directory.
	- [x] Validate inputs before creating output directories and keep runs isolated.
	- [x] Add integration coverage using fixture forecast/event artifacts and verify export round trips.
- [x] Document usage and complete story validation.
	- [x] Document output schemas, frequency units, paths, and optional metric scope.
	- [x] Run focused tests, full offline regressions, and available code-quality checks.
	- [x] Record all changed files and completion evidence, then mark the story for review.

## Dependencies

Story 8.1.

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

- Workflow activated through the documented manual resolver fallback; no workflow
	overrides, project-context file, or sprint-status file is present.
- User approved adding Tasks/Subtasks derived only from this story's requirements.
- Fresh implementation on a clean worktree. Story 8.1 is implemented and available
	at status `review`; existing aggregation owns metric and comparability validation.
- Builder red phase failed on the missing API. Green phase passed all 57 comparison
	unit cases, including 12 new cases. Full offline regression: 1046 passed.
	Editor diagnostics are clean; no standalone lint/typecheck is configured.
- Export red phase failed on the missing writer. Combined validation first found
	a pytest module-name collision; renaming the integration file resolved it.
	Green phase: 66 focused cases passed, including nine new integration cases.
- Writer full offline regression: `uv run pytest -q` -> 1055 passed. Editor
	diagnostics and whitespace checks passed. Three overlong new test lines were
	wrapped; the focused suite and touched-code line-length checks then passed.
- Documentation/completion-record regression: `uv run pytest -q` -> 1055 passed.
	All five changed files have clean editor diagnostics; whitespace and touched-code
	line-length checks pass. File List matches the actual changed-file inventory.

### Completion Notes

- Implementation plan: wrap existing strategy aggregation with run/evaluation
	metadata, then persist run-scoped CSV and Parquet tables through explicit inputs.
	Reuse existing metric semantics and avoid CLI, dashboard, plotting, or training work.
- Built comparison tables with typed run IDs and UTC nanosecond bounds, including
	typed empty results. Existing validation and metric behavior remain unchanged.
- Added an explicit writer producing matching CSV and Parquet files under the
	caller-configured `reports/tables/<run_id>/` directory. Validation occurs before
	directory creation. Safe run IDs prevent traversal; re-exporting replaces only
	the selected run's tables. Export paths are returned to callers.
- Integration coverage reads small persisted forecast/event fixtures and verifies
	metric values, window boundaries, stable schemas, CSV/Parquet round trips,
	missing actuals, zero events, empty logs, non-mutation, run isolation, replacement,
	and validation-before-I/O. Optional directional accuracy remains deferred.
- README documents the schema, configured output directory, UTC half-open period,
	retrains-per-day units, CSV parsing, and subsequent Parquet consumption.
- Added 21 new test cases: 12 unit cases and nine fixture-log integration cases.
	All acceptance criteria are met, all approved task/subtask checkboxes are complete,
	and the original QA Checklist remains unchanged under the story-edit restrictions;
	its conditions are verified by the recorded evidence.
- Definition of done passed: required coverage, full offline regressions, available
	quality checks, usage documentation, scope boundaries, and file inventory.
	No dependencies, credentials, generated report datasets, configuration changes,
	commits, CLI, training, plots, dashboard, AWS, or Docker work were introduced.
	Story is ready for review with no blockers and no sprint tracking configured.

## File List

- `_bmad-output/implementation-artifacts/sprint-8/story-8.2-implement-strategy-comparison-tables.md` (modified)
- `tests/unit/test_strategy_comparison.py` (modified)
- `src/energy_trading_pipeline/evaluation/strategy_comparison.py` (modified)
- `tests/integration/test_strategy_comparison_exports.py` (added)
- `README.md` (modified)

## Change Log

- 2026-10-05: Added the user-approved task checklist and started Story 8.2.
- 2026-10-05: Added comparison metadata and run-scoped CSV/Parquet exports, 21 new
	test cases, and usage documentation; 1055 offline regressions pass.
- 2026-10-05: Passed definition-of-done gates and marked Story 8.2 `review`.
