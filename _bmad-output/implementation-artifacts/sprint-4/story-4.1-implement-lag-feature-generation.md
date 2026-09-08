---
story_id: "4.1"
title: "Implement Lag Feature Generation"
status: "review"
baseline_commit: "fa5b0ded21bcb0e1d33cbdeeeda1840a29ab04e3"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.1: Implement Lag Feature Generation

## Status

review

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a researcher, I want lagged spread and price features so that the model can learn recent market dynamics.

## Description

Generate configured lag features for spread, German price, and French price.

## Acceptance Criteria

Lag columns follow `snake_case`, lags are shifted correctly, rows without sufficient history are handled consistently, generated columns are recorded in metadata.

## Technical Notes

Lag features must never use the target timestamp value as an input for the same prediction timestamp.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/lag_features.py`.

## Testing Requirements

Unit tests verify lag values against a simple ordered fixture.

## Dependencies

Story 3.4.

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

- Story 3.4 (dependency) is merged on main; its `calculate_spread` output is the
  expected input for this story. No sprint-status.yaml or project-context.md
  exists. This story has no separate Tasks/Subtasks section; its description,
  acceptance criteria, and QA checklist governed implementation and completion.
- Used the skill's manual customization fallback because system python3 lacks
  tomllib. No team/user overrides or additional activation steps were present.
- Red: `tests/unit/test_lag_features.py` failed at collection because
  `build_lag_features` did not exist. Green: all 34 unit cases passed after the
  implementation.
- `UV_CACHE_DIR=/private/tmp/energy-trading-uv-cache uv run pytest -q`:
  244 passed (210 pre-existing plus 34 new). Default markers exclude live API,
  AWS, and slow tests.
- `git diff --check` passed. No lint or static-analysis tool is configured.

### Completion Notes

- Implemented `build_lag_features(df, lag_hours, *, columns=...)` returning a
  sorted UTC copy with `<source>_lag_<hours>` columns (default sources `spread`,
  `price_de`, `price_fr`) plus a metadata dict. The input is not mutated;
  pre-existing lag columns of the same name are recomputed.
- Lags are validated as strictly positive integers, de-duplicated, and sorted.
  A lag of zero is rejected explicitly so the target timestamp's own value can
  never feed its own feature. Input must be unique, contiguous hourly data
  (validated with the existing `validate_hourly_index`) so a shift of `n` rows is
  exactly `n` hours; gaps, duplicates, off-hour instants, naive timestamps,
  empty frames, and non-numeric sources fail clearly.
- Insufficient-history policy: rows earlier than the largest lag are retained
  with null lag values. Metadata records `generated_columns`, `lag_hours`,
  `source_columns`, `insufficient_history_policy`, `min_history_hours`,
  `incomplete_history_rows`, and `output_rows` for the dataset builder to
  persist.
- Added 34 unit cases against a six-hour ordered fixture covering shift values,
  snake_case naming and column ordering, no-same-timestamp leakage via
  perturbation, null handling, metadata contents, de-duplication, nonmutation,
  chronological sorting of unsorted input, timezone normalization, recomputed
  columns, invalid lags/columns/dtypes, and non-contiguous data.
- Documented usage, naming, leakage rules, and the null-history policy in
  `docs/lag_features.md`. No new dependencies, config changes, credentials,
  commits, full historical experiments, or future-story (rolling, calendar,
  dataset builder) work were introduced. No blockers remain.

## File List

- `src/energy_trading_pipeline/features/lag_features.py`
- `tests/unit/test_lag_features.py`
- `docs/lag_features.md`
- `_bmad-output/implementation-artifacts/sprint-4/story-4.1-implement-lag-feature-generation.md`

## Change Log

- 2026-09-08: Implemented Story 4.1 leakage-safe lag feature generation with
  metadata, added 34 unit tests on an ordered fixture, and documented usage;
  marked for review.
