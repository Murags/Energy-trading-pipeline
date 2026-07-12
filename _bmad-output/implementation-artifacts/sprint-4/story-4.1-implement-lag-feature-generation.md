---
story_id: "4.1"
title: "Implement Lag Feature Generation"
status: "Ready for Dev"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.1: Implement Lag Feature Generation

## Status

Ready for Dev

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a researcher, I want lagged spread and price features so that the model can learn recent market dynamics.

## Description

Generate configured lag features for spread, German price, and French price.

## Acceptance Criteria

Lag columns follow `snake_case`, lags are shifted correctly, rows without sufficient history are handled consistently, generated columns are recorded in metadata.

## Technical Notes

Lag features must never use the target timestamp value as an input for the same prediction timestamp.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/lag_features.py`.

## Testing Requirements

Unit tests verify lag values against a simple ordered fixture.

## Dependencies

Story 3.4.

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
