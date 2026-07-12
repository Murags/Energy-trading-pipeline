---
story_id: "9.2"
title: "Implement Streamlit Dashboard Views"
status: "Ready for Dev"
parent_epic: "Epic 9: Dashboard Reading Exported Artifacts Only"
priority: "P1"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 9.2: Implement Streamlit Dashboard Views

## Status

Ready for Dev

## Parent Epic

Epic 9: Dashboard Reading Exported Artifacts Only

## Priority

P1

## Suggested Sprint

Sprint 9

## User Story

As an analyst, I want to view forecasts, actual spreads, rolling RMSE, retraining events, and strategy comparisons so that I can inspect model behavior.

## Description

Build a Streamlit app with charts and tables from exported artifacts.

## Acceptance Criteria

Dashboard shows forecast vs actual, RMSE/MAE summaries, rolling RMSE, retraining events, model version changes, and strategy comparison; strategy filters are available; app starts without credentials.

## Technical Notes

Keep app simple and avoid overbuilding UI.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/dashboard/app.py`, `src/energy_trading_pipeline/dashboard/charts.py`.

## Testing Requirements

Smoke test imports app modules and validates chart functions on fixtures.

## Dependencies

Story 9.1.

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
