---
story_id: "10.1"
title: "Add GitHub Actions Fixture-Based CI"
status: "Ready for Dev"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P1"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
---

# Story 10.1: Add GitHub Actions Fixture-Based CI

## Status

Ready for Dev

## Parent Epic

Epic 10: Docker, GitHub Actions, and Reproducibility Support

## Priority

P1

## Suggested Sprint

Sprint 2

## User Story

As a developer, I want CI checks so that regressions are caught without requiring credentials or large datasets.

## Description

Add `.github/workflows/ci.yml` to install dependencies and run pytest on fixture datasets.

## Acceptance Criteria

CI runs on pull requests and pushes, installs project dependencies, runs `pytest`, does not require ENTSO-E or AWS credentials, does not run the full 2020-2025 backtest.

## Technical Notes

Keep CI lightweight; use fixture data only.

## Files / Modules Likely Affected

`.github/workflows/ci.yml`, `tests/`.

## Testing Requirements

Workflow should pass with current fixture tests.

## Dependencies

Stories 1.2 and 1.5.

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
