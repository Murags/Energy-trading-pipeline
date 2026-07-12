---
story_id: "4.2"
title: "Implement Leakage-Safe Rolling Features"
status: "Ready for Dev"
parent_epic: "Epic 4: Feature Engineering with Leakage Prevention"
priority: "P0"
suggested_sprint: "Sprint 4"
source: "_bmad-output/epics.md"
---

# Story 4.2: Implement Leakage-Safe Rolling Features

## Status

Ready for Dev

## Parent Epic

Epic 4: Feature Engineering with Leakage Prevention

## Priority

P0

## Suggested Sprint

Sprint 4

## User Story

As a researcher, I want rolling features that exclude future values so that backtest results are valid.

## Description

Generate configured rolling means and standard deviations for spread and price variables using shifted windows.

## Acceptance Criteria

Rolling windows are shifted before aggregation where required, rolling feature names include window size, insufficient windows are handled consistently, leakage tests fail if current/future values are included incorrectly.

## Technical Notes

This is a high-risk research-validity story; keep implementation explicit and tested.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/features/rolling_features.py`.

## Testing Requirements

Unit tests compare expected rolling values and verify no current timestamp leakage.

## Dependencies

Story 4.1.

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
