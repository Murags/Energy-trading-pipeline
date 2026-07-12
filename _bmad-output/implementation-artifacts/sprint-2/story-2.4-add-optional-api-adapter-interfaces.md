---
story_id: "2.4"
title: "Add Optional API Adapter Interfaces"
status: "Ready for Dev"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P1"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
---

# Story 2.4: Add Optional API Adapter Interfaces

## Status

Ready for Dev

## Parent Epic

Epic 2: Local Data Loading and Artifact Handling

## Priority

P1

## Suggested Sprint

Sprint 2

## User Story

As a developer, I want optional API adapter interfaces so that ENTSO-E and Open-Meteo fetching can be added without changing downstream modules.

## Description

Add interface-style functions or classes for ENTSO-E and Open-Meteo clients with explicit not-configured behavior.

## Acceptance Criteria

API adapters are importable, missing credentials produce clear skip/fallback messages, downstream code can depend on local cached files instead, no API call is made in tests by default.

## Technical Notes

Do not implement full API fetching here; preserve local-first MVP.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/data_ingestion/entsoe_client.py`, `src/energy_trading_pipeline/data_ingestion/open_meteo_client.py`.

## Testing Requirements

Unit tests verify missing credentials do not break local loading path.

## Dependencies

Story 2.2.

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
