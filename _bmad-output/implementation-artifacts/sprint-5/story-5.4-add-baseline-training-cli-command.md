---
story_id: "5.4"
title: "Add Baseline Training CLI Command"
status: "Ready for Dev"
parent_epic: "Epic 5: XGBoost Model Training and Model Registry"
priority: "P0"
suggested_sprint: "Sprint 5"
source: "_bmad-output/epics.md"
---

# Story 5.4: Add Baseline Training CLI Command

## Status

Ready for Dev

## Parent Epic

Epic 5: XGBoost Model Training and Model Registry

## Priority

P0

## Suggested Sprint

Sprint 5

## User Story

As a researcher, I want a CLI command for baseline training so that model creation is reproducible from config.

## Description

Add CLI support to load feature data, train the model, save artifacts, and write training metadata.

## Acceptance Criteria

Command runs on fixture feature data, writes model artifact and metadata, uses configured model parameters, fails clearly if feature dataset is missing.

## Technical Notes

Do not implement backtesting or retraining in this story.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/cli.py`, `src/energy_trading_pipeline/models/trainer.py`.

## Testing Requirements

Integration test invokes training CLI against fixture data.

## Dependencies

Story 5.3.

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
