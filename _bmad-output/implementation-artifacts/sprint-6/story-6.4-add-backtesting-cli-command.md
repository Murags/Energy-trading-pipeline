---
story_id: "6.4"
title: "Add Backtesting CLI Command"
status: "review"
baseline_commit: "1f52d5b0cee3c7d425775debbaf9fe404b3a377d"
parent_epic: "Epic 6: Backtesting Engine and Forecast Logging"
priority: "P0"
suggested_sprint: "Sprint 6"
source: "_bmad-output/epics.md"
---

# Story 6.4: Add Backtesting CLI Command

## Status

review

## Parent Epic

Epic 6: Backtesting Engine and Forecast Logging

## Priority

P0

## Suggested Sprint

Sprint 6

## User Story

As a researcher, I want a CLI command for backtesting so that historical experiments can be rerun from config.

## Description

Add CLI support to run a small or configured backtest and write run metadata, forecast logs, and backtest logs.

## Acceptance Criteria

CLI runs a small fixture backtest, writes outputs under `logs/runs/run_*`, accepts config path, and does not require dashboard, AWS, or external API credentials.

## Technical Notes

Full strategy comparison happens later; this command establishes execution path.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/backtesting/backtest_runner.py`.

## Testing Requirements

Integration test invokes CLI on fixture data.

## Dependencies

Story 6.3.

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

- Implemented on 2026-10-05. Story 6.3 is available (status `review`) and all
  15 runner integration tests passed before implementation. Story scope matches
  the approved Epic 6 entry. No sprint-status file exists; progress is tracked here.
- Added `backtest --config` with the existing optional `--paths-config` and
  `--model-params-config` flags. CLI dispatch delegates to
  `run_configured_backtest`; reusable orchestration stays in `backtesting/`.
- The configured runner reads local feature Parquet, requires explicit
  `backtest.feature_columns` and model parameters, and executes the existing
  static `no_retraining` path. Other configured strategies fail clearly.
- Preserved the existing leakage contract: availability annotations are supplied
  by the caller, never fabricated. Missing annotations and predictors unavailable
  at issuance fail through the CLI. Training and forecast ordering remain owned
  by the existing runner and splitter.
- Successful execution writes `forecasts.parquet`, `run_metadata.yaml`, and
  `backtest_log.jsonl` under `<logs_dir>/runs/run_YYYYMMDD_HHMMSS/`. Metadata links
  the saved model under `<models_dir>/artifacts/model_YYYYMMDD_HHMMSS/model.json`
  and records resolved configuration, data range, ordered predictors, target,
  parameters, strategy, actual initial training window, held-out validation
  window, evaluation window, window convention, and artifact paths.
- JSONL events record start/completion or execution failure with run ID, model
  version, strategy, evaluation range, and error/forecast count. Existing run and
  model directories are never overwritten; failed execution retains diagnostics.
- Validation remains held out but unscored, and `metrics` is explicitly `{}`.
  Model provenance is recorded in run metadata rather than adding unevaluated
  entries to the training registry's validation-metric index. Aggregate metrics
  and strategy comparison remain outside this story.
- README documents command usage, inline/companion config, required availability
  annotations, timing semantics, artifact locations, failure behavior, and the
  fixture verification command.
- All acceptance criteria and QA checks verified: local fixture CLI execution,
  configurable paths/horizon, expected artifacts, and no credential requirements.
  No dependencies, external integrations, dashboard, Docker, retraining policies,
  or full historical experiments were added. Test artifacts stay in temporary
  directories; no secrets or generated datasets were committed.
- This story has no Tasks/Subtasks section. Its original QA checklist is retained
  under the workflow's permitted-section edit rules; completed verification is
  recorded here. No implementation blockers remain.

### Debug Log

- Workflow customization was resolved manually after system Python lacked
  `tomllib`: defaults only, no team/user overrides, no project-context file.
- Dependency verification:
  `uv run pytest tests/integration/test_backtest_runner_small_range.py -q` —
  **15 passed**.
- RED: `uv run pytest tests/integration/test_backtest_cli.py -q` — **13 failed**
  because the backtest command and configured runner entry point were absent.
- GREEN: the same command — **13 passed** after implementation. Cases cover
  subprocess CLI execution without credentials, 24-hour and clipped 7-hour
  horizons, output schemas/provenance, train-only predictions, companion config,
  required inputs, unsupported strategy, invalid windows, availability checks,
  failure logs, and run/model collisions.
- Full regression: `uv run pytest -q` — **737 passed**.
- `uv run python -m energy_trading_pipeline.cli --help` — successful; advertises
  `train` and `backtest` plus configuration flags.
- `git diff --check` — passed. No lint/static-analysis tool is configured in
  `pyproject.toml`; changed code was reviewed against the coding style guide.

## File List

- `src/energy_trading_pipeline/cli.py` — command parsing and dispatch/output.
- `src/energy_trading_pipeline/backtesting/backtest_runner.py` — configured runner,
  run provenance, collision protection, and structured events.
- `tests/integration/test_backtest_cli.py` — 13 fixture-based integration cases.
- `README.md` — backtest usage and input/output contract.
- `_bmad-output/implementation-artifacts/sprint-6/story-6.4-add-backtesting-cli-command.md`
  — baseline, status, implementation and verification record.

## Change Log

- 2026-10-05: Added config-driven backtesting CLI, local run artifacts and logs,
  fixture integration coverage, and usage documentation. Marked ready for review.
