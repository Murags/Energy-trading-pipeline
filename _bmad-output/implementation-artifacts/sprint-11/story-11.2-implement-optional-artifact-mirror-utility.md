---
story_id: "11.2"
title: "Implement Optional Artifact Mirror Utility"
status: "Ready for Dev"
parent_epic: "Epic 11: Optional AWS Artifact Mirroring"
priority: "P2"
suggested_sprint: "Sprint 11"
source: "_bmad-output/epics.md"
---

# Story 11.2: Implement Optional Artifact Mirror Utility

## Status

Ready for Dev

## Parent Epic

Epic 11: Optional AWS Artifact Mirroring

## Priority

P2

## Suggested Sprint

Sprint 11

## User Story

As a developer, I want an optional artifact mirroring utility so that selected local outputs can be copied to S3 when credentials are available.

## Description

Add utility or script that uploads selected report/log/model artifacts to configured S3 prefixes.

## Acceptance Criteria

Utility is disabled unless AWS config is present, missing credentials produce a clear skip message, local runs are unaffected, mirrored paths match local artifact layout.

## Technical Notes

Mark AWS tests separately and mock S3 interactions.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/utils/io.py`, optional `src/energy_trading_pipeline/utils/aws.py`, `configs/experiment.yaml`.

## Testing Requirements

Unit tests use mocks and are marked to avoid real AWS calls.

## Dependencies

Story 11.1.

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
