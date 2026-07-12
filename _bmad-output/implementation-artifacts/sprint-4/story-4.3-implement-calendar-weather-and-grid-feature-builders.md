---
story_id: "4.3"
title: "Implement Calendar, Weather, and Grid Feature Builders"
status: "Ready for Dev"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.3: Implement Calendar, Weather, and Grid Feature Builders

## Status

Ready for Dev

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a researcher, I want calendar, weather, and grid predictors so that the model can use relevant exogenous signals.

## Description

Generate hour, day-of-week, month, weekend flag, optional holiday flag, and pass-through or transformed weather/grid predictors when available.

## Acceptance Criteria

Calendar features are deterministic, optional weather/grid variables warn and continue if unavailable, feature selection is config-driven, output uses canonical `snake_case` column names.

## Technical Notes

Avoid target-derived features in this story except already approved lag/rolling features.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/calendar_features.py`, `weather_features.py`, `grid_features.py`.

## Testing Requirements

Unit tests for calendar extraction and optional-variable behavior.

## Dependencies

Story 4.2.

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
