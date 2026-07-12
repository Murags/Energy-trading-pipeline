---
story_id: "2.3"
title: "Add Fixture Datasets for Local Tests"
status: "Ready for Dev"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P0"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
---

# Story 2.3: Add Fixture Datasets for Local Tests

## Status

Ready for Dev

## Parent Epic

Epic 2: Local Data Loading and Artifact Handling

## Priority

P0

## Suggested Sprint

Sprint 2

## User Story

As a developer, I want small fixture datasets so that CI and local tests can run without credentials or large files.

## Description

Create minimal German price, French price, weather, and optional grid/load fixture files covering enough hourly rows to test alignment and simple backtesting.

## Acceptance Criteria

Fixtures include timestamp, German price, French price, and weather columns; fixture date range is small; fixtures contain at least one missing-value or duplicate case for validation tests.

## Technical Notes

Fixture data may be synthetic and must not represent research results.

## Files / Modules Likely Affected

`tests/fixtures/sample_prices_de.csv`, `tests/fixtures/sample_prices_fr.csv`, `tests/fixtures/sample_weather.csv`, `tests/fixtures/sample_config.yaml`.

## Testing Requirements

Loader tests consume these fixtures.

## Dependencies

Story 2.1.

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
