---
story_id: "9.1"
title: "Implement Dashboard Artifact Loader"
status: "Ready for Dev"
parent_epic: "Epic 9: Dashboard Reading Exported Artifacts Only"
priority: "P1"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 9.1: Implement Dashboard Artifact Loader

## Status

Ready for Dev

## Parent Epic

Epic 9: Dashboard Reading Exported Artifacts Only

## Priority

P1

## Suggested Sprint

Sprint 9

## User Story

As an analyst, I want the dashboard to load exported artifacts so that results can be viewed without rerunning experiments.

## Description

Implement dashboard-only loaders for forecast, metric, retraining event, and model version exports.

## Acceptance Criteria

Loader reads from `reports/dashboard_exports/`, validates expected files/columns, returns display-ready DataFrames, fails with clear user-facing messages for missing exports.

## Technical Notes

Loader must not import or invoke backtesting, training, or ingestion functions.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/dashboard/data_loader.py`.

## Testing Requirements

Unit tests load dashboard fixture exports and handle missing files.

## Dependencies

Story 8.4.

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
