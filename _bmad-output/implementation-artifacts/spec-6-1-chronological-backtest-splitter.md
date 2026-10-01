---
title: 'Story 6.1: Implement Chronological Backtest Splitter'
type: 'feature'
created: '2026-10-01'
status: 'done'
baseline_commit: '636c30baa455e23c6573fb4a77dac79ba181166d'
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/CODING_STYLE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/sprint-6/story-6.1-implement-chronological-backtest-splitter.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The splitter is a placeholder. Configuration lacks evaluation dates and validation duration.

**Approach:** Generate immutable train/validation/forecast windows from explicit dates and durations, with a configuration adapter and leakage-boundary tests.

## Boundaries & Constraints

**Always:** Scope to Story 6.1. Use UTC, positive integer durations, clear `ValueError` messages, inclusive input calendar dates, and half-open output intervals `[start, end)`. Preserve baseline training behavior.

**Ask First:** Changes to the approved window semantics, forecast issuance assumptions, or existing training APIs.

**Never:** Train models, execute backtests, implement policies, write forecast artifacts, or add dependencies. Market publication timing and feature availability require separate runner validation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Normal range | Inclusive evaluation dates, training days, validation days, horizon hours | Ordered windows cover every evaluation hour exactly once | None |
| Historical boundaries | Forecast block starts at `t` | Validation ends at `t`; training ends at validation start; both exclude their upper endpoint | Reject inverted/empty intervals |
| Small debug run | Same start/end date, horizon one hour | 24 hourly forecast windows | None |
| Partial final block | Horizon does not divide evaluation duration, or exceeds it | Final forecast interval ends at midnight after evaluation end date | None |
| Invalid dates | Missing, malformed, reversed, or timestamp-valued calendar bounds | No windows returned | Field-specific `ValueError`; reject time-of-day rather than truncating |
| Invalid duration | Zero, negative, boolean, fractional, or missing required value | No implicit fallback | Field-specific `ValueError` |
| Representation limits | Dates/durations cannot be represented by timestamp arithmetic | No partial results | Clear `ValueError` |
| Configuration | Explicit `backtest` mapping with all required settings | Same windows as direct arguments | Missing/non-mapping settings fail clearly |

</frozen-after-approval>

## Code Map

- `src/energy_trading_pipeline/models/trainer.py` — `TrainingWindow` uses inclusive calendar dates; compatibility reference only.
- `tests/unit/test_training_window.py` — existing boundary-test conventions.
- `tests/integration/test_training_cli.py` — Story 5.4 verification; implementation is merged and available although its artifact says `review`.

## Tasks & Acceptance

**Execution:**
- [x] `src/energy_trading_pipeline/backtesting/splitter.py` — implement `TimeWindow`, `BacktestWindow`, `generate_backtest_windows`, and `generate_backtest_windows_from_config`; document endpoints.
- [x] `configs/experiment.yaml`, `tests/fixtures/sample_config.yaml` — add `backtest.evaluation_start_date`, `evaluation_end_date`, and `validation_window_days`: January 6–8, 2023, one validation day; retain three training days and 24-hour horizon.
- [x] `tests/unit/test_backtest_splitter.py` — cover the matrix, deterministic generation, config equivalence, and hourly timestamp membership.
- [x] `_bmad-output/implementation-artifacts/sprint-6/story-6.1-implement-chronological-backtest-splitter.md` — record implementation and verification results.

**Acceptance Criteria:**
- Given valid configuration, when generating windows, then train precedes validation precedes forecast, and forecast blocks are ordered.
- Given boundary timestamps, when checking membership, then validation/forecast targets cannot enter that block's training interval and forecasts stay within evaluation bounds.
- Given a one-day debug range, when generating windows, then it succeeds without data files or credentials.
- Given invalid bounds/durations, when calling a generator, then a descriptive error precedes any returned windows.

## Spec Change Log

## Design Notes

For forecast start `t`, train is `[t - validation_duration - training_duration, t - validation_duration)`; validation is `[t - validation_duration, t)`. Advance forecast blocks by the horizon, clipping the final end. These rolling candidate windows do not mandate retraining. Earlier evaluation observations may enter later history, never at/after that block's forecast start.

`TimeWindow` has UTC-aware `start`/exclusive `end`; `BacktestWindow` has `train`, `validation`, `forecast`. The direct generator takes `start_date`, `end_date`, `train_window_days`, `forecast_horizon_hours`, and required keyword `validation_window_days`. Accept strict date strings and date objects, excluding datetimes. The adapter reads five explicit `config['backtest']` settings. No model-layer dependency.

## Verification

**Commands:**
- `uv run pytest -q tests/unit/test_backtest_splitter.py tests/unit/test_training_window.py tests/unit/test_config_loader.py tests/integration/test_training_cli.py` — new behavior and existing temporal/config/training contracts pass on fixtures.
- `uv run pytest -q` — default credential-free regression suite passes.
- `git diff --check` — no whitespace errors.

Verify independently constructed hourly timestamp membership. No lint/static-analysis tool is configured.

### Step 03 Results — 2026-10-01

- Focused command above: **176 passed in 3.09s** (final run).
- Full `uv run pytest -q`: **639 passed in 6.05s**.
- `git diff --check`: passed.
- Independent hourly row membership, exact boundary probes, malformed dates and
  durations, calendar transitions, final-block clipping, and representation limits
  are covered. Existing temporal/configuration/training regression tests pass.
- All execution tasks are complete. Original Story 6.1 is `review` with its QA
  checklist and verification record updated; this spec remains `in-progress` for
  parent review. Frozen approved intent and baseline are unchanged.
- No implementation blockers. Publication timing and feature availability remain
  separate runner validation responsibilities per the approved scope.

### Review Results — 2026-10-01

- Completed blind, edge-case, and acceptance review passes. No acceptance violations.
- Patched a pandas 3 duration-resolution edge case: explicitly normalize durations
  to nanoseconds during validation so overflow raises a field-specific `ValueError`.
  Added three regression cases for durations just beyond that representation limit.
- Final `uv run pytest -q`: **642 passed in 6.43s**; `git diff --check` passed.
- All accepted review findings resolved; no blockers or deferred defects.
- Original story remains `review` for human review. No sprint-status file exists.

## Suggested Review Order

**Window generation and leakage boundaries**

- Start with the public contract and rolling historical window construction.
  [`splitter.py:98`](../../src/energy_trading_pipeline/backtesting/splitter.py#L98)
- Validate interval chronology and UTC endpoints before using them in a schedule.
  [`splitter.py:22`](../../src/energy_trading_pipeline/backtesting/splitter.py#L22)
- Reject malformed dates and oversized durations before arithmetic.
  [`splitter.py:68`](../../src/energy_trading_pipeline/backtesting/splitter.py#L68)

**Configuration and evidence**

- Read explicit evaluation settings without silently deriving baseline dates.
  [`splitter.py:176`](../../src/energy_trading_pipeline/backtesting/splitter.py#L176)
- Inspect the small-range configuration example.
  [`experiment.yaml:28`](../../configs/experiment.yaml#L28)
- Check independent timestamp membership and shared-boundary exclusion.
  [`test_backtest_splitter.py:49`](../../tests/unit/test_backtest_splitter.py#L49)
- Review representation-limit regression coverage.
  [`test_backtest_splitter.py:206`](../../tests/unit/test_backtest_splitter.py#L206)
