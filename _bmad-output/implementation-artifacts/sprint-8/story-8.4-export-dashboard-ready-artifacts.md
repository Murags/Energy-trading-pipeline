---
story_id: "8.4"
title: "Export Dashboard-Ready Artifacts"
status: "Ready for Dev"
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P0"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.4: Export Dashboard-Ready Artifacts

## Status

Ready for Dev

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P0

## Suggested Sprint

Sprint 8

## User Story

As an analyst, I want dashboard-ready exported artifacts so that the dashboard can read results without running the pipeline.

## Description

Write forecast, metric, retraining event, and model version artifacts to `reports/dashboard_exports/`.

## Acceptance Criteria

Exports include `forecasts.parquet`, `metrics.parquet`, `retraining_events.parquet`, and `model_versions.parquet`; exports contain only columns needed by the dashboard; export command can run independently after backtests.

## Technical Notes

This story enforces the artifact-only dashboard contract.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/evaluation/exports.py`, `reports/dashboard_exports/`.

## Testing Requirements

Integration test verifies dashboard export files and schemas.

## Dependencies

Story 8.3.

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
