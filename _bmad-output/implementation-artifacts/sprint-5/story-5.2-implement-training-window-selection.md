---
story_id: "5.2"
title: "Implement Training Window Selection"
status: "review"
baseline_commit: "55a021152be3f3679f9ffaa56d316458319721f8"
parent_epic: "Epic 5: XGBoost Model Training and Model Registry"
priority: "P0"
suggested_sprint: "Sprint 5"
source: "_bmad-output/epics.md"
---

# Story 5.2: Implement Training Window Selection

## Status

review

## Parent Epic

Epic 5: XGBoost Model Training and Model Registry

## Priority

P0

## Suggested Sprint

Sprint 5

## User Story

As a researcher, I want chronological training windows so that model fitting avoids future data leakage.

## Description

Implement training dataset selection by configured train/validation date ranges and reusable window parameters.

## Acceptance Criteria

Training rows precede validation/evaluation rows, date ranges are config-driven, invalid overlapping ranges fail clearly, selected feature/target arrays are returned consistently.

## Technical Notes

This supports later backtesting and retraining windows.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/models/trainer.py`, `src/energy_trading_pipeline/backtesting/splitter.py` if shared.

## Testing Requirements

Unit tests for valid chronological split and invalid overlapping split.

## Dependencies

Story 5.1.

## Implementation Notes

- Implement only the scope described in this story.
- Preserve the architecture boundaries defined in `_bmad-output/architecture.md`.
- Do not add adjacent features, dashboard work, AWS work, Docker work, or modelling work unless this story explicitly calls for it.
- Keep reusable project logic under `src/energy_trading_pipeline/` unless the story targets configuration, tests, docs, infrastructure, or repository metadata.
- Use `snake_case` for Python modules, functions, variables, dataframe columns, and artifact identifiers.

## Tasks / Subtasks

- [x] Add config-driven train/validation date ranges (AC: config-driven ranges)
  - [x] Add `train_start_date`, `train_end_date`, `validation_start_date`, and `validation_end_date` to the `dates` section of `configs/experiment.yaml` and `tests/fixtures/sample_config.yaml`
  - [x] Read the four bounds via `TrainingWindow.from_config(config["dates"])`, failing when a key is missing rather than defaulting from `dates.start_date`/`dates.end_date`
- [x] Implement the reusable `TrainingWindow` window parameters (AC: reusable window parameters)
  - [x] Frozen dataclass normalizing each bound to a `date`, constructible directly for later backtesting/retraining windows
  - [x] `as_metadata()` returns serializable bounds for run and model registry metadata
- [x] Fail clearly on invalid or overlapping ranges (AC: invalid overlapping ranges fail clearly)
  - [x] Reject `train_end_date >= validation_start_date`, including a shared boundary date, since both ranges are end-inclusive
  - [x] Reject inverted ranges and unparsable `YYYY-MM-DD` bounds
- [x] Implement `select_training_window` chronological row selection (AC: training rows precede validation rows)
  - [x] Match rows on `timestamp` against end-inclusive calendar days, sorting defensively so output is chronological
  - [x] Verify against the selected rows that the last training timestamp precedes the first validation timestamp
  - [x] Fail clearly when a range selects no rows or a required column is absent
- [x] Return feature/target arrays consistently (AC: consistent feature/target arrays)
  - [x] Same feature columns in the same order on both sides, excluding `timestamp` and the target
  - [x] Target as a `Series` named for the target column, indices reset, aligned timestamps returned alongside
  - [x] Optional explicit `feature_columns` to pin the feature contract for retraining
- [x] Add unit tests for valid chronological split and invalid overlapping split (Testing Requirements)
- [x] Document the module and the new configuration keys

## Dev Agent Instructions

- Read `_bmad-output/architecture.md` and `_bmad-output/epics.md` before implementation.
- Confirm dependencies listed above are completed or available before starting.
- Make the smallest correct implementation that satisfies the acceptance criteria.
- Add or update tests listed in the testing requirements.
- Do not require external credentials unless the story explicitly concerns optional external integration.
- Do not run full 2020-2025 experiments for story verification unless explicitly required.


## Dev Agent Record

### Implementation Plan

`trainer.py` was a docstring-only stub. Implemented two units in it, keeping
`backtesting/splitter.py` untouched since Epic 6 owns it and nothing is shared yet:

- `TrainingWindow` — the reusable window parameters. Validation lives in
  `__post_init__`, so an invalid window fails before any data is touched, and a
  window built directly (as backtesting and retraining will) gets the same
  guarantees as one read from config.
- `select_training_window` — row selection returning a `TrainingSplit`.

Key decisions:

- **End-inclusive day bounds.** A bound is a calendar date but the dataset is
  hourly, so `train_end_date: 2023-01-06` covers through `2023-01-06T23:00`.
  Implemented as a half-open upper bound at `end_date + 1 day` so it holds
  regardless of the dataset's resolution.
- **A shared boundary date is an overlap.** With end-inclusive ranges,
  `train_end_date == validation_start_date` would put the same 24 rows on both
  sides, so the guard is `>=` rather than `>`.
- **No defaulting from `dates.start_date`/`dates.end_date`.** All four window
  keys are required; an implied split point would silently decide which rows a
  model is scored on. Missing keys fail with the required list.
- **Leakage verified on the selected rows, not just the declared bounds.** After
  selection, the last training timestamp is checked to precede the first
  validation timestamp, so a duplicated or misparsed timestamp cannot reach a
  fitted model.
- **Feature contract matches the 5.1 wrapper.** Features exclude `timestamp` and
  the target on both sides in the same order, so `split.train_features` and
  `split.train_target` go straight into `XGBoostSpreadModel.fit`. Timestamps are
  returned alongside because the feature frames exclude them and forecast
  logging needs the row identity back.
- **Out-of-range window warns rather than fails.** The window is still
  chronological, and an empty selection already fails with the covered range.

### Debug Log

- Full suite after implementation: 1 failure, `test_config_loader.py::test_repository_sample_configs_load_with_debug_safe_defaults`, which asserts the fixture config `dates` section exactly. Updated that assertion to include the four new window keys — the config change is intended and covered by the story.
- Mutation-checked the two core guards to confirm the new tests are not vacuous:
  - Weakening the overlap guard from `>=` to `>` → `test_shared_boundary_date_is_rejected_as_an_overlap` fails.
  - Making the upper bound exclusive of the end date's day → 4 tests fail.
  - Both restored; 19/19 pass.

### Completion Notes

Implemented config-driven chronological training window selection in
`models/trainer.py`, satisfying all four acceptance criteria:

- **Training rows precede validation/evaluation rows** — enforced by the window
  guard and re-verified against the actually selected rows.
- **Date ranges are config-driven** — four required keys in the `dates` section,
  read by `TrainingWindow.from_config`.
- **Invalid overlapping ranges fail clearly** — overlap (including a shared
  boundary date), inverted ranges, unparsable dates, missing keys, empty
  selections, and reserved/missing feature columns all raise `ValueError` with a
  message naming the offending bound or column.
- **Selected feature/target arrays are returned consistently** — `TrainingSplit`
  carries the same feature columns in the same order on both sides, targets as
  named `Series`, reset indices, and aligned timestamps.

Tests: 19 new unit tests in `tests/unit/test_training_window.py`, covering the
required valid chronological split and invalid overlapping split, plus boundary
inclusivity, out-of-order input, naive timestamps, input immutability, explicit
feature columns, and metadata. Full suite: **476 passed**, no regressions. No
linter is configured in this repo; CI runs pytest only.

Scope held: no model fitting, artifact persistence, registry metadata, CLI, or
backtesting work was added — those are stories 5.3, 5.4, and Epic 6.
`backtesting/splitter.py` was deliberately left as its Epic 6 stub.

### File List

- `src/energy_trading_pipeline/models/trainer.py` (modified — implemented the stub)
- `tests/unit/test_training_window.py` (added)
- `configs/experiment.yaml` (modified — added the four `dates` window keys)
- `tests/fixtures/sample_config.yaml` (modified — added the four `dates` window keys)
- `tests/unit/test_config_loader.py` (modified — fixture `dates` assertion covers the new keys)
- `docs/training_window.md` (added)
- `_bmad-output/implementation-artifacts/sprint-5/story-5.2-implement-training-window-selection.md` (modified — story record)

### Change Log

- 2026-09-08 — Implemented `TrainingWindow` and `select_training_window` in `models/trainer.py`; added config-driven train/validation date ranges, overlap and chronology validation, and consistent feature/target array selection. Added 19 unit tests and `docs/training_window.md`. Status: Ready for Dev → review.

## QA Checklist

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.
