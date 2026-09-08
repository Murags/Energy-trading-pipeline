---
story_id: "3.3"
title: "Align Market, Grid, and Weather Data Hourly"
status: "review"
baseline_commit: "e09c0f761ef02bd73b923aa940ed6ef66227196b"
parent_epic: "Epic 3: Data Preprocessing and Spread Calculation"
priority: "P0"
suggested_sprint: "Sprint 3"
source: "_bmad-output/epics.md"
---

# Story 3.3: Align Market, Grid, and Weather Data Hourly

## Status

review

## Parent Epic

Epic 3: Data Preprocessing and Spread Calculation

## Priority

P0

## Suggested Sprint

Sprint 3

## User Story

As a researcher, I want all input datasets aligned to hourly delivery periods so that model inputs are consistent.

## Description

Join German price, French price, weather, and optional grid/load/generation data onto a common hourly timestamp index.

## Acceptance Criteria

Aligned output includes one row per hourly timestamp, required price columns are present, optional weather/grid columns are included when available, alignment range follows config start/end dates.

## Technical Notes

Do not generate lag or rolling model features in this story.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/preprocessing/alignment.py`, `data/processed/aligned_hourly/`.

## Testing Requirements

Integration test aligns sample price and weather fixtures.

## Dependencies

Story 3.2.

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

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Debug Log

- Story 3.2's normalization/cleaning dependency is implemented and available;
  its story remains in review. No sprint-status.yaml or project-context.md exists.
- BMAD customization resolution used the documented manual fallback because
  system python3 is older than 3.11. No team/user overrides were present.
- Red: `uv run pytest tests/unit/test_alignment.py tests/integration/test_hourly_alignment.py -q`
  failed collection because `align_hourly_data` was not yet implemented.
- Green: the same command passed all 33 initial tests. Six further edge-case
  tests were added for empty/out-of-range sources, excluded-column collisions,
  and missing required sources; all 39 alignment tests pass.
- Full regression: `uv run pytest -q` passed 178 tests. Default markers exclude
  live API, AWS, and slow tests. No full historical experiment was run.
- `git diff --check` passed. No lint/static-analysis tool is configured.
- Separate implementation/test inspection found no actionable correctness or
  acceptance-criteria issues.

### Completion Notes

- Implemented a single dataframe-level function accepting explicit config date
  values, required German/French sources, and optional weather/grid frames.
- Calendar-date bounds include both full UTC dates; the January 1-8 fixture
  range produces exactly 192 sorted hourly rows. Source order and timezone do
  not change delivery-instant matching. Inputs remain unmodified.
- Required price columns and complete hourly coverage fail fast when missing.
  Duplicate instants, off-hour values, malformed timestamps, duplicate column
  names, and cross-source column collisions fail rather than silently merge.
- Missing/empty optional sources warn; optional columns with missing aligned
  values are excluded and reported. Complete optional columns are retained.
  There is no interpolation, forward/backfill, resampling, or feature generation.
- Returned metadata records UTC bounds, row count, retained/excluded columns,
  absent optional sources, and missing-value counts before exclusions.
- Added 38 unit cases and one local loader/normalization/cleaning/alignment
  integration test using existing price and weather fixtures. Coverage includes
  range clipping, required endpoint/interior gaps, DST-distinct instants,
  optional coverage, validation failures, and input nonmutation.
- Documented API usage, inclusive date semantics, missingness policy, and the
  distinction between delivery-time alignment and forecast-time availability.
- Scope matches the approved Story 3.3 entry. Spread calculation and processed
  Parquet/source metadata persistence remain in Story 3.4; no CLI work added.
- No dependencies, generated datasets, credentials, commits, or future-story
  implementation were introduced. No implementation blockers remain.

## File List

- `src/energy_trading_pipeline/preprocessing/alignment.py`
- `tests/unit/test_alignment.py`
- `tests/integration/test_hourly_alignment.py`
- `docs/hourly_alignment.md`
- `_bmad-output/implementation-artifacts/sprint-3/story-3.3-align-market-grid-and-weather-data-hourly.md`

## Change Log

- 2026-09-08: Implemented Story 3.3 hourly alignment, explicit coverage and
  optional-column rules, usage documentation, and 39 tests; marked for review.
