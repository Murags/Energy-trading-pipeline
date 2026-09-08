---
story_id: "4.2"
title: "Implement Leakage-Safe Rolling Features"
status: "review"
baseline_commit: "50137415d2bbf7ac1cc08ded63faafdef36c9787"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.2: Implement Leakage-Safe Rolling Features

## Status

review

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a researcher, I want rolling features that exclude future values so that backtest results are valid.

## Description

Generate configured rolling means and standard deviations for spread and price variables using shifted windows.

## Acceptance Criteria

Rolling windows are shifted before aggregation where required, rolling feature names include window size, insufficient windows are handled consistently, leakage tests fail if current/future values are included incorrectly.

## Technical Notes

This is a high-risk research-validity story; keep implementation explicit and tested.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/rolling_features.py`.

## Testing Requirements

Unit tests compare expected rolling values and verify no current timestamp leakage.

## Dependencies

Story 4.1.

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

- Story 4.1 (dependency) is merged on main; its `build_lag_features` module is the
  structural precedent and its output shares the same processed hourly input. No
  sprint-status.yaml or project-context.md exists. This story has no separate
  Tasks/Subtasks section; its description, acceptance criteria, and QA checklist
  governed implementation and completion.
- Used the skill's manual customization fallback because system python3 lacks
  tomllib. No team/user overrides or additional activation steps were present.
- Red: `tests/unit/test_rolling_features.py` failed at collection because
  `build_rolling_features` did not exist. Green: 46 cases passed after the
  implementation, once one incorrect test expectation was corrected (it used the
  pre-perturbation value of the perturbed row rather than the preceding row).
- Mutation-checked the leakage tests, since the acceptance criteria require that
  they fail on incorrect current/future inclusion. Removing the shift fails 11
  tests, centring the window fails 10, `ROLLING_SHIFT_HOURS = 0` fails 12, and
  `min_periods=1` fails 9. The module was restored and byte-diffed against a
  pre-mutation copy to confirm no residue.
- `UV_CACHE_DIR=/private/tmp/energy-trading-uv-cache uv run pytest -q`:
  290 passed (244 pre-existing plus 46 new). Default markers exclude live API,
  AWS, and slow tests.
- Sanity-checked the configured `features.rolling_window_hours: [24]` on a
  30-hour frame: 24 leading incomplete rows, and row 24 equals the mean of rows
  0-23 exactly.
- `git diff --check` passed. No lint or static-analysis tool is configured.

### Completion Notes

- Implemented `build_rolling_features(df, window_hours, *, columns=...)` returning
  a sorted UTC copy with `<source>_rolling_<statistic>_<window_hours>` columns
  (default sources `spread`, `price_de`, `price_fr`; statistics `mean` and `std`)
  plus a metadata dict. The input is not mutated; pre-existing rolling columns of
  the same name are recomputed rather than duplicated.
- Shift-before-aggregate: each source is shifted by `ROLLING_SHIFT_HOURS = 1`
  *before* `.rolling(...)`, so a row's window covers the `n` hours strictly before
  it and never includes its own or any later value. A rolling mean over window
  `n` therefore equals the mean of lags `1..n`, asserted directly against Story
  4.1's `build_lag_features` as a cross-check.
- Window names always carry the window size, so multiple configured windows
  cannot collide. Windows are validated as integers of at least
  `MIN_ROLLING_WINDOW_HOURS = 2`, de-duplicated, and sorted; a one-hour window is
  rejected explicitly because its standard deviation is undefined and would emit
  a silently all-null column. Standard deviations use `ddof=1`, recorded in
  metadata.
- Insufficient-window policy: windows aggregate only when complete
  (`min_periods` equals the window), so a partial window is never silently
  reported as a shorter-window statistic. Leading rows and windows spanning a
  null source value both yield nulls and are retained rather than dropped,
  matching Story 4.1's policy. Metadata records `generated_columns`,
  `window_hours`, `statistics`, `source_columns`, `shift_hours`, `std_ddof`,
  `insufficient_window_policy`, `min_history_hours`, `incomplete_window_rows`,
  and `output_rows` for the dataset builder to persist.
- Input must be unique, contiguous hourly data (validated with the existing
  `validate_hourly_index`) so a window of `n` rows is exactly `n` hours; gaps,
  duplicates, off-hour instants, naive timestamps, empty frames, duplicate column
  names, and non-real-numeric sources fail clearly.
- Added 46 unit cases against an eight-hour ordered fixture. Expected rolling
  values are computed with `statistics.fmean`/`stdev` over explicit Python slices
  rather than pandas, so the tests are an independent reference. Coverage spans
  mean/std values, window-size naming and column ordering, current-timestamp and
  future-value leakage via perturbation, partial-window nulls, null propagation,
  metadata contents, de-duplication, source overrides, nonmutation, chronological
  sorting, timezone normalization, recomputed columns, the lag cross-check, and
  the full set of invalid inputs.
- Documented naming, the shift rule, the minimum window, and the null-window
  policy in `docs/rolling_features.md`. No new dependencies, config changes,
  credentials, commits, full historical experiments, or future-story (calendar,
  weather, grid, dataset builder) work were introduced. No blockers remain.

## File List

- `src/energy_trading_pipeline/features/rolling_features.py`
- `tests/unit/test_rolling_features.py`
- `docs/rolling_features.md`
- `_bmad-output/implementation-artifacts/sprint-4/story-4.2-implement-leakage-safe-rolling-features.md`

## Change Log

- 2026-09-08: Implemented Story 4.2 leakage-safe rolling mean/std features with
  shift-before-aggregate windows and metadata, added 46 mutation-checked unit
  tests on an ordered fixture, and documented usage; marked for review.
