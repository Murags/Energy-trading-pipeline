---
story_id: "3.1"
title: "Implement Timestamp Normalization"
status: "review"
baseline_commit: e8489094505aa192c98f5d823fbc84bcfc9e4968
parent_epic: "Epic 3: Data Preprocessing and Spread Calculation"
priority: "P0"
suggested_sprint: "Sprint 3"
source: "_bmad-output/epics.md"
---

# Story 3.1: Implement Timestamp Normalization

## Status

review

## Parent Epic

Epic 3: Data Preprocessing and Spread Calculation

## Priority

P0

## Suggested Sprint

Sprint 3

## User Story

As a researcher, I want timestamps normalized consistently so that all datasets align correctly across sources.

## Description

Implement timestamp parsing, timezone normalization, hourly index validation, and daylight-saving-time handling.

## Acceptance Criteria

Timestamp column is parsed reliably, modelling timestamps are normalized consistently, non-hourly or ambiguous timestamps are reported, DST handling is documented in metadata.

## Technical Notes

Default policy should normalize modelling timestamps to UTC while preserving source timezone metadata where useful.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/preprocessing/timestamps.py`, `src/energy_trading_pipeline/preprocessing/validation.py`.

## Testing Requirements

Unit tests cover normal hourly data, missing hours, duplicate timestamps, and DST-like edge cases.

## Dependencies

Story 2.3.

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

### Completion Notes

- Implemented only Story 3.1; acceptance criteria match the approved Epic 3 entry.
- Story 2.3 fixture datasets and loader tests are available; its status remains
  `review`, not formally done. No dependency implementation was needed.
- `normalize_timestamps` returns a stable chronologically sorted dataframe copy
  and explicit JSON/YAML-serializable metadata. Naive values use the supplied
  source timezone (UTC default); aware values preserve their original instant.
- Ambiguous/nonexistent naive DST times fail with input row context. Explicit
  offsets resolve repeated fall-back hours. No DST inference, shifting, dropping,
  interpolation, or other cleaning was introduced.
- Hourly validation reports internal gaps, duplicate instants, off-hour values,
  and sorting. Issues are retained in metadata and logged as warnings. Required
  invalid, missing, empty, or unparsed timestamp inputs fail clearly.
- Source timezone/offset information and DST policy are returned for callers to
  persist with subsequent stage artifacts; no artifact writer or CLI was added.
- Added usage and policy documentation in `docs/timestamp_normalization.md`.
- No dependencies, configuration defaults, external services, generated datasets,
  modelling, dashboard, AWS, Docker, or future-story behavior were added.
- Pre-existing changes in `.gitignore`, `_bmad-output/epics.md`, Story 2.5, and
  `docs/data_sources.md` were left untouched. No commit was made.
- No sprint-status file exists; tracking is confined to this story. The existing
  QA checklist is left for review; implementation verification is recorded here.

### Verification

- [x] Reliable parsing, UTC normalization, chronological ordering, and input preservation.
- [x] Missing-hour, duplicate-instant, and non-hourly reporting without cleaning.
- [x] Berlin/Paris DST cases and explicit DST/source timezone metadata.
- [x] Unit tests on small inputs and existing Story 2.3 fixtures.
- [x] Documentation, story-only scope, and architecture boundary checks.

### Debug Log

- Red phase: `uv run pytest tests/unit/test_timestamps.py` failed collection with
  the expected missing `normalize_timestamps` import before implementation.
- Green phase: `uv run pytest tests/unit/test_timestamps.py`: 30 passed.
- Regression: `uv run pytest`: 109 passed on Python 3.14.4 / pandas 3.0.3.
- Quality: `git diff --check` passed. No linter, formatter, or static type checker
  is configured in `pyproject.toml`.
- The BMAD customization resolver could not run under system Python (<3.11);
  customization was resolved manually from the default TOML, with no overrides.
- No blockers or incomplete implementation work remain.

## File List

- `src/energy_trading_pipeline/preprocessing/timestamps.py` (modified)
- `src/energy_trading_pipeline/preprocessing/validation.py` (modified)
- `tests/unit/test_timestamps.py` (added)
- `docs/timestamp_normalization.md` (added)
- `_bmad-output/implementation-artifacts/sprint-3/story-3.1-implement-timestamp-normalization.md` (modified)

## Change Log

- 2026-09-08: Implemented UTC timestamp normalization, explicit DST rejection and
  metadata, hourly validation reports, 30 focused tests, and usage documentation.
  All 109 regression tests pass; status set to `review`.
