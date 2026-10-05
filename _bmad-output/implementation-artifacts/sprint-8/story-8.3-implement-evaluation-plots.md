---
story_id: "8.3"
title: "Implement Evaluation Plots"
status: "review"
baseline_commit: 264f159821f8d0bf8bab4f8a05cc73ec4570ce6d
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P1"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.3: Implement Evaluation Plots

## Status

review

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P1

## Suggested Sprint

Sprint 8

## User Story

As a researcher, I want plots for forecasts, rolling RMSE, retraining events, and strategy comparison so that results are easy to interpret.

## Description

Generate report-ready figures using Matplotlib or Plotly from exported forecast and metric artifacts.

## Acceptance Criteria

Forecast-vs-actual plot is generated, rolling RMSE plot is generated, retraining event visualization is generated, strategy comparison plot is generated, figures are written under `reports/figures/`.

## Technical Notes

Keep plotting separate from metric calculations.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/evaluation/plots.py`, `reports/figures/`.

## Testing Requirements

Smoke tests verify plot files are created from small fixtures.

## Tasks/Subtasks

- [x] Generate the forecast-vs-actual figure from exported forecast data.
	- [x] Add failing fixture tests, implement headless rendering, and verify chronological, non-mutating plots.
- [x] Generate the rolling RMSE figure from stored monitoring values.
	- [x] Add failing tests, preserve missing-history gaps, and avoid metric recalculation.
- [x] Generate the completed-retraining event visualization.
	- [x] Add failing tests and represent an empty event log explicitly.
- [x] Generate the strategy comparison figure from Story 8.2 tables.
	- [x] Add failing tests and show stored error metrics, retraining count, and frequency with distinct units.
- [x] Verify artifact-based figure generation and document usage.
	- [x] Add smoke coverage reading small persisted artifacts and writing all four run-scoped figures under the configured reports/figures directory.
	- [x] Document required columns, missing-data handling, and output paths.
	- [x] Run full offline regressions and available quality checks; record all changed files and mark the story for review.

## Dependencies

Story 8.2.

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

- Activated through the documented manual customization fallback. No overrides,
	project-context file, or sprint-status file exists.
- User approved adding the missing Tasks/Subtasks section from existing acceptance
	criteria. Fresh implementation on a clean worktree; Story 8.2 is available at
	status `review`. Matplotlib is already a core dependency.
- Forecast red phase: 12 failures on missing API. Green phase: 12 passed.
	Full offline regression: 1067 passed. Touched Python editor diagnostics clean.
- Rolling RMSE red phase: six failures on missing API. Green phase: 18 plot tests
	passed; full offline regression: 1073 passed.
- Event timeline red phase: six failures on missing API. Green phase: 24 plot
	tests passed; full offline regression: 1079 passed.
- Comparison red phase: 13 failures on missing API. First green run exposed a
	NumPy assertion requiring an array rather than a pandas Series; corrected the
	test and reran. Green phase: 37 plot tests passed; full regressions: 1092 passed.
- Artifact smoke tests: eight CSV/Parquet cases passed for normal, empty, no-events,
	and no-scores inputs. Verified PNG signatures, dimensions, nonblank pixels,
	input preservation, run isolation, and safe replacement.
- Visual inspection exposed Matplotlib's single-timestamp event axis expansion
	to 1606 days. Added a failing regression and constrained that case to a two-hour
	view. All 46 focused tests now pass. One overlong source line was wrapped.
- Final implementation validation: `uv run pytest -q` -> 1101 passed. All five
	changed files have clean editor diagnostics. Whitespace and touched-code
	88-column checks pass. No standalone lint/typecheck command is configured.
- Completion-gate regression rerun: 1101 passed. All approved Tasks/Subtasks are
	checked, the final changed-file inventory matches File List, and whitespace
	validation passes. Definition of done passed; story status set to `review`.

### Completion Notes

- Implementation plan: render stored forecast, monitoring, completed-event, and
	comparison artifacts through explicit dataframe inputs and a configured figures
	directory. Use headless Matplotlib and run-scoped PNG files; do not calculate
	metrics or introduce CLI, dashboard, training, AWS, or Docker behavior.
- Forecast-vs-actual output preserves negative spreads and missing actuals, sorts
	aware timestamps into UTC, checks shared timelines/actuals, and validates before
	writing. Empty logs produce an explicit no-data figure. Inputs are not mutated.
- Rolling RMSE plots use stored monitoring values verbatim, preserve gaps, reject
	negative/infinite metrics, and identify insufficient history explicitly.
- Completed-event timelines show all three canonical strategy lanes, exact UTC
	event timestamps, and explicit empty-log messages without inferring events.
- Comparison figures display all four stored core metrics with distinct units,
  canonical strategy ordering, run/evaluation metadata, and unavailable-score
  labels. Mixed runs/windows and invalid numeric values fail before filesystem I/O.
- Added artifact-based fixture smoke coverage and README usage/schema documentation.
	Four 180-DPI PNGs are generated under caller-configured reports/figures paths,
	isolated by run ID. No generated research results are committed.
- Added 46 test cases: 38 unit cases and eight persisted-artifact integration
	cases. Verified all acceptance criteria, approved task checkboxes, and scope
	boundaries. The original QA Checklist is unchanged under story-edit restrictions;
	its conditions are verified by the tests and completion evidence.
- File List contains all five changed files. No dependencies, secrets, committed
	generated datasets, configuration changes, CLI, dashboard, modelling, AWS, or
	Docker work were introduced. No blockers or sprint-status tracking file exists.
- Story 8.3 is complete and ready for review. All definition-of-done gates passed;
  the story is tracked here only because no sprint-status file is configured.

## File List

- `_bmad-output/implementation-artifacts/sprint-8/story-8.3-implement-evaluation-plots.md` (modified)
- `tests/unit/test_evaluation_plots.py` (added)
- `src/energy_trading_pipeline/evaluation/plots.py` (modified)
- `tests/integration/test_evaluation_plot_artifacts.py` (added)
- `README.md` (modified)

## Change Log

- 2026-10-05: Added the user-approved task list, captured baseline, and started Story 8.3.
- 2026-10-05: Implemented four headless report figure APIs, 46 fixture test cases,
  and README usage documentation; 1101 offline tests and available quality checks pass.
- 2026-10-05: Passed final definition-of-done gates and marked Story 8.3 `review`.
