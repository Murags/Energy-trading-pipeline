---
story_id: "3.2"
title: "Implement Missing and Duplicate Record Cleaning"
status: "review"
baseline_commit: "0ae13c98236d205016e722a1c205c5f9243c6393"
parent_epic: "Epic 3: Data Preprocessing and Spread Calculation"
priority: "P0"
suggested_sprint: "Sprint 3"
source: "_bmad-output/epics.md"
---

# Story 3.2: Implement Missing and Duplicate Record Cleaning

## Status

review

## Parent Epic

Epic 3: Data Preprocessing and Spread Calculation

## Priority

P0

## Suggested Sprint

Sprint 3

## User Story

As a researcher, I want missing and duplicate records handled reproducibly so that preprocessing decisions are auditable.

## Description

Implement cleaning utilities that detect duplicates, summarize missingness, apply configured missing-value rules, and write preprocessing logs.

## Acceptance Criteria

Duplicate timestamps are detected, missing values are counted by column, required missing values fail or are handled by configured rule, optional missing values warn and continue, cleaning decisions are logged.

## Technical Notes

Keep rules simple and documented; avoid silent imputation.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/preprocessing/cleaning.py`, `src/energy_trading_pipeline/preprocessing/validation.py`, `logs/runs/*/preprocessing_log.jsonl`.

## Testing Requirements

Unit tests for duplicate detection and missing-value behavior.

## Dependencies

Story 3.1.

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

### Implementation Plan

- Use Story 3.1's available timestamp normalization implementation; that story
  remains in review. Preserve UTC instant identity and stable duplicate ordering.
- Add read-only record summaries and a single cleaning function with explicit
  policies, source-specific required/optional columns, and an injected run directory.
- Resolve duplicates before required nulls; avoid imputation and hourly alignment.
- Persist successful and failed cleaning decisions to append-only JSONL records.

### Debug Log

- Red: `uv run pytest tests/unit/test_cleaning.py -q` failed at collection because
  `clean_records` did not yet exist.
- Green: `uv run pytest tests/unit/test_cleaning.py tests/unit/test_timestamps.py -q`
  passed all 55 tests before adding five further cleaning edge-case tests.
- Final regression: `uv run pytest -q` passed all 139 tests, including 30 new
  cleaning tests. Default markers exclude external API, AWS, and slow tests.
- `git diff --check` passed. No lint/static-analysis tool is configured.
- The system `python3` cannot resolve BMAD TOML customizations because it is older
  than 3.11; activation used the documented manual fallback. Project tests use uv.

### Completion Notes

- Duplicate detection reports surplus rows and distinct UTC instants; configurable
  `raise` or stable `keep_first` handling never averages conflicting prices.
- Missingness is counted for every input column. Absent required columns always
  fail; required null cells support `raise` or `drop_rows`. Empty results fail.
- Missing optional columns and optional columns with input nulls warn and are
  excluded, with reduced columns explicitly recorded. Undeclared extras are optional.
- Audits include run/dataset/stage, input date range, policies, counts, affected
  timestamps, excluded/retained columns, and errors. Log failures prevent success.
- Added explicit fail-fast YAML defaults and documented call order, rules, and
  audit usage. Inputs are not mutated; no filling or future-story work was added.
- Tests cover fixtures, null/absent columns, stable/conflicting duplicates,
  equivalent offsets and DST-distinct instants, invalid input/rules, multi-column
  row removal, append-only audit round trips, and storage failure.
- No dependencies, generated datasets, credentials, or commits were added.
- No sprint-status.yaml exists; status is tracked in this story only.

## File List

- `src/energy_trading_pipeline/preprocessing/cleaning.py`
- `src/energy_trading_pipeline/preprocessing/validation.py`
- `configs/experiment.yaml`
- `docs/record_cleaning.md`
- `tests/unit/test_cleaning.py`
- `_bmad-output/implementation-artifacts/sprint-3/story-3.2-implement-missing-and-duplicate-record-cleaning.md`

## Change Log

- 2026-09-08: Implemented Story 3.2 cleaning, record summaries, JSONL auditing,
  configured defaults, documentation, and 30 tests; marked ready for review.
