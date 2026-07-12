---
story_id: "3.3"
title: "Align Market, Grid, and Weather Data Hourly"
status: "Ready for Dev"
parent_epic: "Epic 3: Data Preprocessing and Spread Calculation"
priority: "P0"
suggested_sprint: "Sprint 3"
source: "_bmad-output/epics.md"
---

# Story 3.3: Align Market, Grid, and Weather Data Hourly

## Status

Ready for Dev

## Parent Epic

Epic 3: Data Preprocessing and Spread Calculation

## Priority

P0

## Suggested Sprint

Sprint 3

## User Story

As a researcher, I want all input datasets aligned to hourly delivery periods so that model inputs are consistent.

## Description

Join German price, French price, weather, and optional grid/load/generation data onto a common hourly timestamp index.

## Acceptance Criteria

Aligned output includes one row per hourly timestamp, required price columns are present, optional weather/grid columns are included when available, alignment range follows config start/end dates.

## Technical Notes

Do not generate lag or rolling model features in this story.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/preprocessing/alignment.py`, `data/processed/aligned_hourly/`.

## Testing Requirements

Integration test aligns sample price and weather fixtures.

## Dependencies

Story 3.2.

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
