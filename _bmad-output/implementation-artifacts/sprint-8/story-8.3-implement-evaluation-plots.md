---
story_id: "8.3"
title: "Implement Evaluation Plots"
status: "Ready for Dev"
parent_epic: "Epic 8: Evaluation Outputs and Report Artifacts"
priority: "P1"
suggested_sprint: "Sprint 8"
source: "_bmad-output/epics.md"
---

# Story 8.3: Implement Evaluation Plots

## Status

Ready for Dev

## Parent Epic

Epic 8: Evaluation Outputs and Report Artifacts

## Priority

P1

## Suggested Sprint

Sprint 8

## User Story

As a researcher, I want plots for forecasts, rolling RMSE, retraining events, and strategy comparison so that results are easy to interpret.

## Description

Generate report-ready figures using Matplotlib or Plotly from exported forecast and metric artifacts.

## Acceptance Criteria

Forecast-vs-actual plot is generated, rolling RMSE plot is generated, retraining event visualization is generated, strategy comparison plot is generated, figures are written under `reports/figures/`.

## Technical Notes

Keep plotting separate from metric calculations.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/evaluation/plots.py`, `reports/figures/`.

## Testing Requirements

Smoke tests verify plot files are created from small fixtures.

## Dependencies

Story 8.2.

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
