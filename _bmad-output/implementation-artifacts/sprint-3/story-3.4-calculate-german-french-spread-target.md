---
story_id: "3.4"
title: "Calculate German-French Spread Target"
status: "review"
baseline_commit: "e37d47491ee1a88a8726c7563ac4a69d51421247"
parent_epic: "Epic 3: Data Preprocessing and Spread Calculation"
priority: "P0"
suggested_sprint: "Sprint 3"
source: "_bmad-output/epics.md"
---

# Story 3.4: Calculate German-French Spread Target

## Status

review

## Parent Epic

Epic 3: Data Preprocessing and Spread Calculation

## Priority

P0

## Suggested Sprint

Sprint 3

## User Story

As a researcher, I want the target spread calculated consistently so that all downstream modelling uses the same target variable.

## Description

Add spread calculation as `spread = price_de - price_fr` and persist processed aligned output.

## Acceptance Criteria

Output includes `spread`, calculation is verified against known fixture values, processed dataset is saved as Parquet, metadata records source files and date range.

## Technical Notes

Use canonical column names `price_de`, `price_fr`, and `spread`.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/preprocessing/spread.py`, `data/processed/aligned_hourly/`.

## Testing Requirements

Unit test validates spread arithmetic and processed Parquet output.

## Dependencies

Story 3.3.

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

- Story 3.3's alignment implementation is available; its story remains in review.
  No sprint-status.yaml or project-context.md exists. This story has no separate
  Tasks/Subtasks section; its description, acceptance criteria, and QA checklist
  governed implementation and completion.
- Used the skill's manual customization fallback because system python3 lacks
  tomllib. No team/user overrides or additional activation steps were present.
- Red: targeted pytest collection failed because calculate_spread and
  save_processed_data did not yet exist. Green: all 29 initial unit cases passed.
- Added three further unit cases and extended the existing 192-hour fixture
  integration test through spread calculation, Parquet reload, and YAML checks.
- `UV_CACHE_DIR=/private/tmp/energy-trading-uv-cache uv run pytest -q`:
  210 passed. The cache override avoids the sandbox-restricted default uv cache.
  Default markers exclude live API, AWS, and slow tests.
- `git diff --check` passed. No lint or static-analysis tool is configured.

### Completion Notes

- Implemented calculate_spread as a nonmutating dataframe transformation using
  canonical German-minus-French arithmetic. Output is sorted and UTC-normalized;
  optional columns are retained, and any stale spread is recalculated.
- Reused existing timestamp validators. Missing required columns, invalid prices,
  empty data, duplicate/off-hour delivery instants, and hourly gaps fail clearly.
  Float arithmetic avoids unsigned/integer wraparound; non-finite output fails.
- Implemented save_processed_data with an explicit configured path and source
  mapping. Parquet contains the complete aligned frame and target; its YAML
  sidecar records source files, actual UTC date range, row count, columns, target
  formula, artifact paths, and optional alignment metadata.
- Updated the default processed destination to
  data/processed/aligned_hourly/prices.parquet and documented both public APIs,
  caller-supplied provenance, validation, and processed-file replacement behavior.
- Added 32 unit cases covering known positive/negative/zero arithmetic,
  nonmutation, unsigned and nullable values, invalid inputs, overflow, Parquet
  persistence, and source/date metadata. Extended the fixture integration test
  and adjusted the config destination assertion.
- All acceptance criteria are satisfied. Generated test artifacts remain in
  temporary directories. No new dependencies, credentials, commits, full historical
  experiments, or future-story implementation were introduced. No blockers remain.

## File List

- `src/energy_trading_pipeline/preprocessing/spread.py`
- `configs/local_paths.yaml`
- `docs/hourly_alignment.md`
- `tests/unit/test_spread_calculation.py`
- `tests/unit/test_config_loader.py`
- `tests/integration/test_hourly_alignment.py`
- `_bmad-output/implementation-artifacts/sprint-3/story-3.4-calculate-german-french-spread-target.md`

## Change Log

- 2026-09-08: Implemented Story 3.4 spread calculation and processed Parquet/YAML
  persistence, updated configured path and usage documentation, added 32 unit
  tests, and extended fixture integration coverage; marked for review.
