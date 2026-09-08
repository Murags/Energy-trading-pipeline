---
story_id: "4.4"
title: "Build Feature Dataset Artifact"
status: "review"
baseline_commit: "dbf0b50"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.4: Build Feature Dataset Artifact

## Status

review

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a developer, I want a feature dataset builder so that modelling and backtesting consume one reproducible artifact.

## Description

Combine feature generation outputs into a canonical feature dataset and metadata file.

## Acceptance Criteria

`data/features/feature_dataset.parquet` is written, metadata records target column, feature columns, source processed dataset, date range, and feature config, builder can run on fixture data.

## Technical Notes

Keep feature generation deterministic from processed data and config.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/dataset_builder.py`, `data/features/`.

## Testing Requirements

Integration test builds a feature dataset from processed fixtures.

## Dependencies

Story 4.3.

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

- Story 4.3 (dependency) is implemented on `feat/implement-calendar-weather-and-grid-feature-builders`
  at `dbf0b50` and is open for review as PR #79, which this branch is stacked on.
  All four upstream builders (lag, rolling, calendar, weather, grid) return the
  same `(dataframe, metadata)` shape, which this story consumes directly. This
  story has no separate Tasks/Subtasks section; its description, acceptance
  criteria, and QA checklist governed implementation and completion.
- Decision: contemporaneous `price_de` and `price_fr` are excluded from the
  feature set. `spread = price_de - price_fr`, so passing either price through at
  the target timestamp would hand the model the target. Their lagged and rolling
  forms remain features. `NON_FEATURE_COLUMNS` is asserted in tests and reported
  in metadata as `excluded_columns`.
- Decision: rows without a complete feature vector are dropped here rather than
  retained. Stories 4.1 and 4.2 deliberately keep null warm-up rows so downstream
  stages can choose; the dataset builder is that downstream stage. Dropping keeps
  every retained row usable by modelling and guarantees all retraining strategies
  compare on identical rows, which `AGENTS.md` requires. The count is recorded as
  `incomplete_rows_dropped`.
- Red: `tests/unit/test_dataset_builder.py` and
  `tests/integration/test_feature_dataset_build.py` failed at collection because
  `build_feature_dataset` and `save_feature_dataset` did not exist. Green: 38
  cases passed after the implementation, once two incorrect test expectations were
  corrected. The warm-up is 3 hours for `lag_hours: [1, 2]` with
  `rolling_window_hours: [3]`, not 4, because a window shifted by one hour first
  completes at row `w` rather than row `w + 1`; and the shared test helper used
  `None` as its "use the default config" sentinel, which swallowed the
  invalid-config case.
- `UV_CACHE_DIR=/private/tmp/energy-trading-uv-cache uv run pytest -q`:
  419 passed (381 from Story 4.3 and earlier, plus 38 new). Default markers
  exclude live API, AWS, and slow tests.
- End-to-end run of the fixture pipeline into the configured artifact path wrote
  `data/features/feature_dataset.parquet` (168 rows x 21 columns, no nulls) and
  `data/features/feature_dataset.metadata.yaml`: target `spread`, 19 feature
  columns, retained range 2023-01-02T00:00:00+00:00 through
  2023-01-08T23:00:00+00:00, 24 warm-up rows dropped for `lag_hours: [1, 24]` and
  `rolling_window_hours: [24]`. `temperature_2m_c` (excluded upstream by
  alignment) and `load_de` (never ingested) each warned once and were left out of
  the feature set without failing the run.
- Both generated artifacts are git-ignored through a new `.gitignore` entry, so
  the artifact path is exercised without committing a generated dataset.
- `git diff --check` passed. No lint or static-analysis tool is configured.

### Completion Notes

- `build_feature_dataset(df, feature_config, *, source_dataset)` runs the lag,
  rolling, calendar, weather, and grid builders in the fixed `FEATURE_STAGE_ORDER`
  over a processed hourly dataset and returns the dataset plus metadata. The
  artifact holds exactly `timestamp`, the `spread` target, and the generated
  feature columns, in that order. The input is not mutated, and colliding column
  names across stages fail rather than silently overwriting one another.
- `save_feature_dataset(df, output_path, *, feature_config, source_dataset)`
  writes the Parquet artifact and a `<name>.metadata.yaml` sidecar, mirroring
  `save_processed_data`. The path is the configured
  `paths.feature_data_parquet_path`, which resolves to
  `data/features/feature_dataset.parquet`; an integration test pins that
  resolution so the acceptance-criteria path stays config-driven rather than
  hard-coded. A non-`.parquet` path fails, and nothing is written when the build
  fails.
- Metadata records `target_column`, `feature_columns`,
  `source_processed_dataset`, `date_range` and `source_date_range`,
  `feature_config` (the normalized settings each stage actually applied),
  `excluded_columns`, `incomplete_row_policy`, `incomplete_rows_dropped`,
  `source_rows`, `output_rows`, each builder's own report under `feature_stages`,
  and `artifact_paths`. A run is therefore reproducible from the processed dataset
  and the metadata alone.
- Determinism: generation is a pure function of the processed data and the config.
  Repeated builds are asserted frame-equal with equal metadata, and a
  reverse-ordered processed input yields the identical dataset because every
  builder sorts chronologically first.
- Config handling: `lag_hours` and `rolling_window_hours` are required and fail
  clearly when absent. The calendar, holiday, weather, and grid keys are optional;
  an absent exogenous key requests no predictors from that group rather than
  guessing which optional variables the processed dataset carries. Unrecognized
  keys warn, so a typo such as `calender_features` does not silently fall back to
  a default. Optional variables that were never ingested warn and are excluded, so
  a price-only processed dataset still builds.
- Added 32 unit cases and 6 integration cases. The integration test runs the real
  fixture pipeline (load, normalize, clean, align, spread, persist) and then builds
  the feature dataset from the persisted processed Parquet, asserting the artifact
  and sidecar are written, the column contract, no nulls, chronological order, the
  24-hour warm-up drop, the metadata contract, the unavailable-variable path, and
  byte-level reproducibility across two builds.
- Documented the artifact, column contract, config handling, incomplete-row policy,
  and metadata in `docs/feature_dataset.md`. No new dependencies, credentials,
  commits of generated data, full historical experiments, or future-story
  (modelling, backtesting, dashboard, AWS, Docker) work were introduced. No CLI
  command was added, because no story in Epic 4 calls for one.
- Observation for a later story, not fixed here to stay in scope: processed
  artifacts at `data/processed/aligned_hourly/` are not git-ignored, unlike the
  run-scoped `data/processed/run_*/` paths, so a local preprocessing run leaves
  untracked generated Parquet in the working tree.

## File List

- `src/energy_trading_pipeline/features/dataset_builder.py`
- `tests/unit/test_dataset_builder.py`
- `tests/integration/test_feature_dataset_build.py`
- `docs/feature_dataset.md`
- `.gitignore`
- `_bmad-output/implementation-artifacts/sprint-4/story-4.4-build-feature-dataset-artifact.md`

## Change Log

- 2026-09-08: Implemented Story 4.4 feature dataset builder and Parquet plus
  metadata artifact persistence, added 32 unit and 6 integration tests, ignored
  the generated artifacts, and documented the artifact contract; marked for
  review.
