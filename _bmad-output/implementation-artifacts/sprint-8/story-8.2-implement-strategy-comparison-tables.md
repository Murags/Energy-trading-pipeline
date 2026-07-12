---
story_id: "8.2"
title: "Implement Strategy Comparison Tables"
status: "Ready for Dev"
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P0"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.2: Implement Strategy Comparison Tables

## Status

Ready for Dev

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P0

## Suggested Sprint

Sprint 8

## User Story

As a researcher, I want strategy comparison tables so that results can be used in the final report.

## Description

Generate summary tables for RMSE, MAE, retraining count, retraining frequency, and optional directional accuracy.

## Acceptance Criteria

Tables are written under `reports/tables/`, strategy identifiers are stable, tables include run ID and evaluation period, output can be read by dashboard later.

## Technical Notes

CSV exports are acceptable for report readability; Parquet can be used for canonical dashboard exports.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/evaluation/strategy_comparison.py`, `reports/tables/`.

## Testing Requirements

Integration test builds comparison table from fixture forecast/event logs.

## Dependencies

Story 8.1.

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
