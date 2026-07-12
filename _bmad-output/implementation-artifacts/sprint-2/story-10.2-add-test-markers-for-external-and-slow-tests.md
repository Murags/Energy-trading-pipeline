---
story_id: "10.2"
title: "Add Test Markers for External and Slow Tests"
status: "Ready for Dev"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P1"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
---

# Story 10.2: Add Test Markers for External and Slow Tests

## Status

Ready for Dev

## Parent Epic

Epic 10: Docker, GitHub Actions, and Reproducibility Support

## Priority

P1

## Suggested Sprint

Sprint 2

## User Story

As a developer, I want API, AWS, and slow tests marked so that CI can skip them safely.

## Description

Define pytest markers for `external_api`, `aws`, and `slow`, and configure CI to exclude them by default.

## Acceptance Criteria

Marker definitions exist, CI command excludes marked tests, API/AWS tests are skipped or mocked by default, documentation explains how to run them locally.

## Technical Notes

This prevents accidental credential or full-backtest requirements in CI.

## Files / Modules Likely Affected

`pyproject.toml`, `tests/`, `.github/workflows/ci.yml`, `README.md`.

## Testing Requirements

Verify marker selection excludes marked tests.

## Dependencies

Story 10.1.

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
