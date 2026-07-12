---
story_id: "12.1"
title: "Write Setup and Reproduction README"
status: "Ready for Dev"
parent_epic: "Epic 12: Documentation and Diagrams"
priority: "P1"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 12.1: Write Setup and Reproduction README

## Status

Ready for Dev

## Parent Epic

Epic 12: Documentation and Diagrams

## Priority

P1

## Suggested Sprint

Sprint 9

## User Story

As a researcher, I want setup and reproduction instructions so that the project can be rerun and evaluated by others.

## Description

Document local virtualenv setup, dependency installation, config files, fixture tests, CLI commands, and output locations.

## Acceptance Criteria

README includes local setup, test command, config explanation, core pipeline command sequence, dashboard command, and notes that Docker/AWS are optional.

## Technical Notes

Keep commands aligned with actual CLI behavior.

## Files / Modules Likely Affected

`README.md`.

## Testing Requirements

Documentation command review against implemented CLI.

## Dependencies

Stories 1.4, 6.4, 8.4, 9.2.

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
