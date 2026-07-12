---
story_id: "12.2"
title: "Create Data Dictionary and Artifact Catalogue"
status: "Ready for Dev"
parent_epic: "Epic 12: Documentation and Diagrams"
priority: "P1"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 12.2: Create Data Dictionary and Artifact Catalogue

## Status

Ready for Dev

## Parent Epic

Epic 12: Documentation and Diagrams

## Priority

P1

## Suggested Sprint

Sprint 9

## User Story

As a researcher, I want a data dictionary and artifact catalogue so that columns and outputs are interpretable in the final report.

## Description

Document canonical columns, feature groups, artifact paths, metadata files, and report outputs.

## Acceptance Criteria

Data dictionary includes `timestamp`, `price_de`, `price_fr`, `spread`, `prediction`, `actual`, `error`, `squared_error`, `absolute_error`, `rolling_rmse`, `strategy`, `model_version`; artifact catalogue maps raw, processed, feature, model, log, report, and dashboard paths.

## Technical Notes

This supports academic traceability.

## Files / Modules Likely Affected

`docs/data_dictionary.md`, `docs/artifacts.md`.

## Testing Requirements

Documentation review against implemented schemas.

## Dependencies

Stories 4.4, 6.2, 8.4.

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
