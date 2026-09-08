---
story_id: "4.3"
title: "Implement Calendar, Weather, and Grid Feature Builders"
status: "review"
baseline_commit: "0127e882104264b77d04868e45945bfb6fe3518e"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.3: Implement Calendar, Weather, and Grid Feature Builders

## Status

review

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a researcher, I want calendar, weather, and grid predictors so that the model can use relevant exogenous signals.

## Description

Generate hour, day-of-week, month, weekend flag, optional holiday flag, and pass-through or transformed weather/grid predictors when available.

## Acceptance Criteria

Calendar features are deterministic, optional weather/grid variables warn and continue if unavailable, feature selection is config-driven, output uses canonical `snake_case` column names.

## Technical Notes

Avoid target-derived features in this story except already approved lag/rolling features.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/calendar_features.py`, `weather_features.py`, `grid_features.py`.

## Testing Requirements

Unit tests for calendar extraction and optional-variable behavior.

## Dependencies

Story 4.2.

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

- Story 4.2 (dependency) is merged on `main` at `0127e88`; its
  `build_rolling_features` module and Story 4.1's `build_lag_features` are the
  structural precedent for the `(dataframe, metadata)` return shape, validation
  style, and appended-column ordering used here. This story has no separate
  Tasks/Subtasks section; its description, acceptance criteria, and QA checklist
  governed implementation and completion.
- Weather and grid selection is the same logic with different default column
  sets, so the shared rules live in one new module,
  `features/optional_features.py`, and the two story modules wrap it with their
  own defaults, stage name, and group name. Duplicating roughly sixty lines of
  validation across two modules was the alternative and was rejected.
- No holiday dependency was added. German and French holiday calendars differ
  and `holidays` is not an approved dependency, so `features.holiday_dates` is
  configuration and `is_holiday` is opt-in.
- Red: the four new test modules failed at collection because
  `build_calendar_features`, `select_optional_features`, `build_weather_features`,
  and `build_grid_features` did not exist. Green: 91 cases passed after the
  implementation, once two incorrect test expectations were corrected. An
  all-`None` column assigned through `DataFrame.assign` becomes `object` dtype, so
  it is rejected as non-numeric rather than as missing values, and
  `datetime.strptime(..., "%Y-%m-%d")` accepts unpadded `2023-1-1`, matching the
  existing `config/schema.py` date parsing, so that case is not invalid.
- `UV_CACHE_DIR=/private/tmp/energy-trading-uv-cache uv run pytest -q`:
  381 passed (290 pre-existing plus 91 new). Default markers exclude live API,
  AWS, and slow tests.
- End-to-end sanity check with the shipped `features` config on the price and
  weather fixtures: `hour`, `day_of_week`, `month`, `is_weekend`, and `is_holiday`
  were generated; 2023-01-01 resolved to day-of-week 6 with `is_weekend` and
  `is_holiday` true for all 24 hours; `temperature_2m_c` (already excluded by
  alignment for missing hours) and `load_de` (never ingested) each warned once
  and were left out of the selected feature set without failing the run.
- `git diff --check` passed. No lint or static-analysis tool is configured.

### Completion Notes

- `build_calendar_features(df, *, features=..., holiday_dates=...)` appends the
  configured calendar columns and returns a sorted UTC copy plus metadata. Every
  column is a pure function of the row's own UTC timestamp, so the output is
  deterministic and cannot depend on any other row; a single-row call reproduces
  the same values as the full frame, which is asserted directly. Integer columns
  use a fixed `int16` width so the artifact dtype does not vary by platform, and
  the flags are `bool`.
- Supported columns are `hour`, `day_of_week` (Monday `0`), `month`,
  `is_weekend` (Saturday and Sunday), and the optional `is_holiday`. Columns are
  always appended in that canonical order and de-duplicated, so configuration
  order never changes the dataset. An unsupported feature name fails with the
  supported list rather than being ignored, because it can only be a config
  mistake. Because no calendar column looks beyond its own row, hourly gaps are
  tolerated here, unlike in the lag and rolling builders.
- `is_holiday` is opt-in and matches the UTC calendar date. Requesting it with no
  configured dates warns, skips the column, and reports it under
  `skipped_features` rather than emitting a uniformly false column that would
  look like a real predictor; configuring dates without requesting the flag warns
  that they are unused. Dates accept ISO strings or `datetime.date` (YAML parses
  an unquoted date that way) and reject instants.
- `build_weather_features` and `build_grid_features` select the configured
  exogenous predictors through the shared `select_optional_features`. A column is
  usable only when present, real numeric, and free of missing or non-finite
  values; usable columns are cast to `float64`. Absent or unusable columns warn
  and are excluded from `selected_columns` instead of failing, leaving a
  documented reduced feature set, and an empty configured list is valid and warns
  about nothing. Nothing is dropped from the returned frame, so the dataset
  builder in Story 4.4 selects features from the metadata.
- Leakage guard: `timestamp`, `price_de`, `price_fr`, and `spread` are rejected as
  optional predictor names, so a contemporaneous price cannot be passed through
  as an exogenous feature. No target-derived features are added by this story;
  lag and rolling features remain the only ones, in their own modules.
- Config-driven selection: added `features.calendar_features`,
  `features.holiday_dates`, `features.weather_columns`, and
  `features.grid_columns` to `configs/experiment.yaml` and
  `tests/fixtures/sample_config.yaml`. `grid_columns` ships empty in the
  experiment config because grid ingestion is optional and not wired; the fixture
  config requests `load_de` so the warn-and-continue path is exercised on fixture
  data.
- Added 91 unit cases across `test_calendar_features.py`,
  `test_optional_features.py`, `test_weather_features.py`, and
  `test_grid_features.py`. Coverage spans calendar values across a
  Friday/Saturday/Sunday fixture, determinism and row-locality, canonical
  ordering and de-duplication, dtypes and `snake_case` naming, holiday matching
  and both holiday warning paths, tolerated gaps, recomputed columns,
  nonmutation, chronological sorting, UTC normalization, optional-column
  selection with missing/all-null/partial-null/non-numeric/non-finite/boolean
  inputs, empty selections, price-only datasets, reserved-column rejection, and
  the full set of invalid inputs.
- Documented the calendar columns, determinism, and holiday policy in
  `docs/calendar_features.md`, and the pass-through and warn-and-continue rules in
  `docs/exogenous_features.md`. No new dependencies, credentials, commits, full
  historical experiments, or future-story (dataset builder, modelling, dashboard,
  AWS, Docker) work were introduced. No blockers remain.

## File List

- `src/energy_trading_pipeline/features/calendar_features.py`
- `src/energy_trading_pipeline/features/optional_features.py`
- `src/energy_trading_pipeline/features/weather_features.py`
- `src/energy_trading_pipeline/features/grid_features.py`
- `configs/experiment.yaml`
- `tests/fixtures/sample_config.yaml`
- `tests/unit/test_calendar_features.py`
- `tests/unit/test_optional_features.py`
- `tests/unit/test_weather_features.py`
- `tests/unit/test_grid_features.py`
- `docs/calendar_features.md`
- `docs/exogenous_features.md`
- `_bmad-output/implementation-artifacts/sprint-4/story-4.3-implement-calendar-weather-and-grid-feature-builders.md`

## Change Log

- 2026-09-08: Implemented Story 4.3 deterministic calendar features and
  config-driven optional weather/grid predictor selection with warn-and-continue
  handling, added 91 unit tests, extended the feature configuration, and
  documented both builders; marked for review.
