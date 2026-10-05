---
story_id: "9.1"
title: "Implement Dashboard Artifact Loader"
status: "review"
baseline_commit: ad08564836857cfd9b1c53e06a0c67da15f0d0c6
parent_epic: "Epic 9: Dashboard Reading Exported Artifacts Only"
priority: "P1"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 9.1: Implement Dashboard Artifact Loader

## Status

review

## Parent Epic

Epic 9: Dashboard Reading Exported Artifacts Only

## Priority

P1

## Suggested Sprint

Sprint 9

## User Story

As an analyst, I want the dashboard to load exported artifacts so that results can be viewed without rerunning experiments.

## Description

Implement dashboard-only loaders for forecast, metric, retraining event, and model version exports.

## Acceptance Criteria

Loader reads from `reports/dashboard_exports/`, validates expected files/columns, returns display-ready DataFrames, fails with clear user-facing messages for missing exports.

## Technical Notes

Loader must not import or invoke backtesting, training, or ingestion functions.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/dashboard/data_loader.py`.

## Testing Requirements

Unit tests load dashboard fixture exports and handle missing files.

## Tasks/Subtasks

- [x] Implement and verify the artifact-only dashboard loader.
	- [x] Write failing unit tests against the four Story 8.4 export schemas.
	- [x] Load all four required Parquet files, validate columns, and return display-ready DataFrames with clear errors for missing exports.
	- [x] Cover empty tables, timestamp preparation, invalid files/columns, source preservation, and forbidden pipeline imports.
	- [x] Document loader usage, run offline regression and quality checks, and record completion for review.

## Dependencies

Story 8.4.

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

- Activated with the documented manual customization fallback because system Python lacks `tomllib`. No customization overrides, project-context file, or sprint-status file exists.
- User approved adding Tasks/Subtasks strictly derived from the acceptance criteria. Fresh implementation with a clean worktree at the recorded baseline; no review follow-ups exist. Story 8.4 is implemented and available at status `review`.
- Red phase: focused tests failed collection because the loader API was absent. First green run: 22 passed, three timestamp dtype assertions failed. Corrected fixtures to match Story 8.4's nanosecond UTC export contract rather than pandas' inferred microsecond timestamps. Focused rerun: 25 passed without warnings.
- Added access-error, duplicate-column, extra-column, and real exporter compatibility checks. Final focused command: `uv run pytest -q tests/unit/test_dashboard_data_loader.py tests/integration/test_dashboard_export_artifacts.py` -> 70 passed.
- Full offline regression: `uv run pytest -q` -> 1185 passed. Touched-file editor diagnostics and `git diff --check` pass. No standalone lint/typecheck command is configured.
- Completion-gate regression rerun: 1185 passed. Automated checks confirm five completed task checkboxes, all five changed files listed, unchanged protected story content, valid Python syntax, unique top-level definitions, and code lines within 88 columns. Protected-section comparison excludes only trailing heading-separator newlines.

### Completion Notes

- Implementation plan: keep display schemas within the dashboard loader rather than importing the exporter, whose dependencies include pipeline stages. Return an explicit mapping of the four saved DataFrames and use one dashboard-specific validation exception for callers.
- Implemented `load_dashboard_artifacts` with a working-directory-relative `reports/dashboard_exports` default and an explicit override for configured locations. All four Parquet files and their expected columns are required, including for empty tables. Extra columns are excluded; duplicate column names are rejected.
- Display preparation normalizes timestamps to nanosecond UTC, rejects invalid/missing timestamps, sorts rows, and resets indexes. Naive timestamps are explicitly interpreted as UTC. Predictions, stored metrics, missing actuals, and unavailable rolling RMSE are preserved without recomputation.
- Missing exports identify their paths and point to `export-dashboard`. Unreadable files retain their underlying exception as the cause; missing columns and invalid timestamps identify the file and field.
- Added 28 unit cases and four producer-to-loader integration cases using small temporary Parquet fixtures. Coverage includes all files, schema errors, corruption/access failures, empty snapshots/events, missing scores, UTC conversion, deterministic display preparation, source byte preservation, and subprocess-enforced forbidden pipeline imports.
- README documents the loader API, custom export locations, return keys, timestamp handling, validation errors, and read-only behavior. No dependencies, configuration changes, generated research artifacts, credentials, UI views, charts, AWS, Docker, or modelling work were introduced.
- All approved Tasks/Subtasks are complete and acceptance criteria are verified. The original QA Checklist is unchanged under story-edit restrictions; its conditions are evidenced by tests and this record. Story progress is tracked here because no sprint-status file exists.
- Story 9.1 is implemented and ready for review with all definition-of-done gates passing and no blockers. Recommended next step: independent code review.

## File List

- `_bmad-output/implementation-artifacts/sprint-9/story-9.1-implement-dashboard-artifact-loader.md` (modified)
- `src/energy_trading_pipeline/dashboard/data_loader.py` (modified)
- `tests/unit/test_dashboard_data_loader.py` (added)
- `tests/integration/test_dashboard_export_artifacts.py` (modified)
- `README.md` (modified)

## Change Log

- 2026-10-05: Added the user-approved task checklist, captured the baseline, and started Story 9.1.
- 2026-10-05: Implemented the artifact-only loader, documented its API, and added 32 fixture test cases. All 1185 offline regressions and available quality checks pass.
- 2026-10-05: Passed the final regression and definition-of-done gates; marked Story 9.1 `review`.
