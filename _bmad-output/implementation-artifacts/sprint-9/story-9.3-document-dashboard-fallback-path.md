---
story_id: "9.3"
title: "Document Dashboard Fallback Path"
status: "review"
baseline_commit: f4a879b81faa611e0ec5636e600f63db52f5cdac
parent_epic: "Epic 9: Dashboard Reading Exported Artifacts Only"
priority: "P2"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 9.3: Document Dashboard Fallback Path

## Status

review

## Parent Epic

Epic 9: Dashboard Reading Exported Artifacts Only

## Priority

P2

## Suggested Sprint

Sprint 9

## User Story

As a researcher, I want a notebook/static report fallback so that the project remains deliverable if dashboard polish is constrained.

## Description

Document how to inspect exported artifacts through notebook or static report outputs if Streamlit is unavailable.

## Acceptance Criteria

README or docs describe Streamlit command, required export files, and fallback notebook/static report path; fallback does not require rerunning the full backtest.

## Technical Notes

This supports the PRD boundary that dashboard should not block core MVP.

## Files / Modules Likely Affected

`README.md`, `notebooks/03_backtest_review.ipynb`, `notebooks/04_report_figures.ipynb`, `docs/`.

## Testing Requirements

Documentation review; optional notebook smoke run on fixture artifacts.

## Tasks/Subtasks

- [x] Document the Streamlit launch command and required export files with a fallback pointer.
- [x] Document an executable static-report fallback that reads existing exports without rerunning backtests.
- [x] Validate the documented fallback on fixtures, run regression checks, and record completion.

## Dependencies

Story 9.2.

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

- Workflow activated with no prepend/append steps; no project-context or sprint-status file exists. English communication/document output and intermediate user skill level loaded from BMM config.
- User approved adding the minimal acceptance-criteria-derived Tasks/Subtasks section because the supplied story had no implementation checklist.
- Fresh implementation from a clean working tree; no review continuation. Story 9.2 is implemented and available at status `review`.
- Task 1 red phase failed on the missing export filenames; green phase passed after the README update. Full offline regression: 1208 passed.
- Task 2 red phase: six expected failures for the missing static-report section. Green phase: seven documentation checks passed, including the executable README example on six fixture scenarios.
- Scenarios cover normal exports, empty events, missing scores, omitted monitoring, an entirely empty snapshot, and a missing required file. Smoke checks forbid Streamlit and pipeline-stage imports and verify all saved input/export bytes remain unchanged.
- Full offline regression after the documentation and test refinements: `uv run --extra dashboard --extra test --extra notebook pytest -q` -> 1214 passed.
- Touched-file editor diagnostics and `git diff --check` pass. Automated quality checks confirm protected story sections/frontmatter are unchanged, all changed files are listed, Python syntax is valid, definitions are unique, and new test functions fit the 88-column style limit. No standalone lint/typecheck command is configured.
- Final completion-gate regression rerun: 1214 passed; all three task checkboxes and required completion records verified before setting status to `review`.

### Completion Notes

- Implementation plan: document the existing artifact loader and headless plotting API in README. Reuse the four exported tables and stored scores; do not introduce notebooks, pipeline changes, new dependencies, or full experiments.
- Documented the four required Parquet files alongside the existing Streamlit command and added the fallback pointer.
- Added the static-report fallback to README: inspect existing per-run CSV/PNG outputs or render all four headless report figures directly from the exported snapshot using the existing loader/plotting API.
- The runnable example prints stored table previews and model metadata, preserves missing scores, handles empty snapshots without inventing a run ID, and writes only the selected run's PNGs. Missing files fail clearly; snapshot recovery uses saved artifacts via the existing export command, not a new backtest.
- Added seven fixture-based documentation checks to the existing export integration test file. No reusable code, notebooks, dependencies, credentials, generated research artifacts, dashboard features, Docker, AWS, modelling, or future-story scope was introduced.
- All three approved tasks and acceptance criteria are satisfied. The original QA Checklist remains unchanged under the story-edit restrictions; its conditions are verified by the documentation review and recorded checks. Progress is tracked here because no sprint-status file exists. No blockers remain.
- Story 9.3 is implemented and ready for review. Recommended next step: independent code review, preferably using a different model.

## File List

- `_bmad-output/implementation-artifacts/sprint-9/story-9.3-document-dashboard-fallback-path.md` (modified)
- `README.md` (modified)
- `tests/integration/test_dashboard_export_artifacts.py` (modified)

## Change Log

- 2026-10-05: Added the user-approved minimal task checklist, captured the baseline, and started Story 9.3.
- 2026-10-05: Documented the launch/export requirements and executable artifact-only static fallback, added seven fixture checks, and passed 1214 offline regressions plus quality checks.
- 2026-10-05: Passed the final completion-gate regression rerun and marked Story 9.3 `review`.
