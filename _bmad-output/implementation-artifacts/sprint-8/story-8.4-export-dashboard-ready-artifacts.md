---
story_id: "8.4"
title: "Export Dashboard-Ready Artifacts"
status: "review"
baseline_commit: 7e83a446d45b065050bcc5ea94578e43f8050ab9
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P0"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.4: Export Dashboard-Ready Artifacts

## Status

review

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P0

## Suggested Sprint

Sprint 8

## User Story

As an analyst, I want dashboard-ready exported artifacts so that the dashboard can read results without running the pipeline.

## Description

Write forecast, metric, retraining event, and model version artifacts to `reports/dashboard_exports/`.

## Acceptance Criteria

Exports include `forecasts.parquet`, `metrics.parquet`, `retraining_events.parquet`, and `model_versions.parquet`; exports contain only columns needed by the dashboard; export command can run independently after backtests.

## Technical Notes

This story enforces the artifact-only dashboard contract.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/evaluation/exports.py`, `reports/dashboard_exports/`.

## Testing Requirements

Integration test verifies dashboard export files and schemas.

## Tasks/Subtasks

- [x] Export the four dashboard-ready Parquet artifacts from saved results.
	- [x] Write failing schema and artifact integration tests before implementation.
	- [x] Select only dashboard columns, preserve UTC timestamps and stored results, and validate inputs before writing.
	- [x] Cover empty events, model version metadata, input preservation, and invalid inputs with fixture tests.
- [x] Provide and verify an independent post-backtest export command.
	- [x] Write failing CLI tests proving exports do not invoke training or backtesting.
	- [x] Implement the command using explicit saved artifact inputs and the configured reports directory.
	- [x] Document command usage and export schemas.
	- [x] Run offline regressions and available quality checks; record changed files and mark the story for review.

## Dependencies

Story 8.3.

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
- User approved adding Tasks/Subtasks derived from the existing acceptance criteria. Fresh implementation; clean worktree at the recorded baseline. Story 8.3 is implemented at status `review`.
- Artifact red phase: 19 failures on the missing export API. Green phase: 19 passed. Structural validation caught overlapping patches introducing duplicate definitions; removed the duplicate block and reran the focused tests successfully.
- Added 14 unit cases. Two failing cases exposed count overflow and an unchecked explicit forecast run ID; repaired both. Focused validation: 33 passed. Full offline regression: 1134 passed.
- CLI red phase: eight cases failed on the missing command; four argument-error cases passed. Green phase: all 12 command cases passed. Added seven command boundary cases for source collisions, invalid metadata/formats, and flags used with other commands.
- The saved backtest run metadata contains version/type but does not register the model or record a creation timestamp. Kept the model export to version/type only and verified both registry and run-metadata paths without inferring creation times.
- Final focused export and CLI validation: 67 passed. Full offline regression: `uv run pytest -q` -> 1153 passed. All touched code/document editor diagnostics and whitespace checks pass. Two overlong CLI lines predate this story; no standalone lint/typecheck command is configured.
- Completion-gate regression rerun: 1153 passed. Automated definition-of-done checks verify nine completed task checkboxes, all six changed files in File List, unchanged protected story sections, valid Python syntax, no duplicate top-level definitions, and no new overlong code lines. Whitespace validation passes.

### Completion Notes

- Implementation plan: project saved evaluation and model metadata into four minimal Parquet artifacts through the evaluation module. Add an independent CLI command that reads explicit artifact paths and writes under the configured reports directory without running pipeline stages.
- Implemented the four minimal, typed Parquet outputs with UTC timestamps, single-run/window checks, chronological forecasts, missing-value preservation, and referenced model metadata only. Stored aggregate and rolling metrics are not recomputed. Optional monitoring uses exact timestamp/strategy keys; unmatched records fail explicitly.
- Artifact API validation passes for empty inputs/events, missing actuals, sparse monitoring, negative spreads, invalid schemas/values, model metadata, source preservation, replacement, and preservation of an existing snapshot when validation fails.
- Added `export-dashboard` with explicit saved table paths and either a registry index or repeated saved backtest run metadata paths. It writes the four files under configured `reports_dir/dashboard_exports`, returns before run bootstrap, and rejects source/output collisions. It never invokes training, backtesting, retraining, model loading, dashboard code, or AWS.
- README documents schemas, configured and explicit path resolution, completed-event provenance, optional decision-time monitoring, static-backtest metadata, and single-writer snapshot replacement. Model version changes remain traceable through timestamped forecasts/events.
- Added 52 test cases: 14 unit and 38 integration cases, including independent in-process CLI checks with forbidden execution hooks and a subprocess command check. No dependencies, configuration changes, generated research artifacts, secrets, or future-story implementation were introduced.
- All approved Tasks/Subtasks are checked and all acceptance criteria are verified. The original QA Checklist remains unchanged under the story-edit restrictions; its conditions are evidenced by the tests, file inventory, and completion record. No sprint-status tracking file exists.
- Story 8.4 is complete and ready for review. All definition-of-done gates passed; status is `review`, tracked in this story only. No blockers remain. Recommended next step: independent code review.

## File List

- `_bmad-output/implementation-artifacts/sprint-8/story-8.4-export-dashboard-ready-artifacts.md` (modified)
- `src/energy_trading_pipeline/evaluation/exports.py` (modified)
- `tests/integration/test_dashboard_export_artifacts.py` (added)
- `tests/unit/test_dashboard_exports.py` (added)
- `src/energy_trading_pipeline/cli.py` (modified)
- `README.md` (modified)

## Change Log

- 2026-10-05: Added the user-approved task list, captured the baseline, and started Story 8.4.
- 2026-10-05: Implemented four minimal Parquet exports and an independent saved-artifact CLI command; documented usage and added 52 fixture tests. All 1153 offline regressions and available quality checks pass.
- 2026-10-05: Passed final definition-of-done and regression gates; marked Story 8.4 `review`.
