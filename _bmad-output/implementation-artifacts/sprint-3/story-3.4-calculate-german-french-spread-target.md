---
story_id: "3.4"
title: "Calculate German-French Spread Target"
status: "Ready for Dev"
parent_epic: "Epic 3: Data Preprocessing and Spread Calculation"
priority: "P0"
suggested_sprint: "Sprint 3"
source: "_bmad-output/epics.md"
---

# Story 3.4: Calculate German-French Spread Target

## Status

Ready for Dev

## Parent Epic

Epic 3: Data Preprocessing and Spread Calculation

## Priority

P0

## Suggested Sprint

Sprint 3

## User Story

As a researcher, I want the target spread calculated consistently so that all downstream modelling uses the same target variable.

## Description

Add spread calculation as `spread = price_de - price_fr` and persist processed aligned output.

## Acceptance Criteria

Output includes `spread`, calculation is verified against known fixture values, processed dataset is saved as Parquet, metadata records source files and date range.

## Technical Notes

Use canonical column names `price_de`, `price_fr`, and `spread`.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/preprocessing/spread.py`, `data/processed/aligned_hourly/`.

## Testing Requirements

Unit test validates spread arithmetic and processed Parquet output.

## Dependencies

Story 3.3.

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
