---
story_id: "2.4"
title: "Add Optional API Adapter Interfaces"
status: "review"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P1"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
baseline_commit: "ed29157a5cb67154e094456e468f62e32a020e3f"
---

# Story 2.4: Add Optional API Adapter Interfaces

## Status

Review

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

## Tasks / Subtasks

- [x] Define importable ENTSO-E and Open-Meteo adapter interfaces.
- [x] Implement clear not-configured skip/fallback behavior without API fetching.
- [x] Add unit coverage proving local cached loading works without credentials or network calls.
- [x] Run the full fixture-based regression suite and configured code-quality checks.

## Dev Agent Record

### Implementation Plan

- Use small adapter classes with configuration state exposed explicitly to callers.
- Log and return no artifact when an adapter is unconfigured, before any future network boundary.
- Exercise the existing local loader as the fallback path and guard tests against network access.

### Debug Log

- Confirmed Story 2.2 is available and provides the local immutable raw cache boundary.
- Confirmed both API client modules were importable placeholders before the red phase.
- Confirmed the focused adapter test failed during collection before the client classes existed.
- Used `UV_CACHE_DIR=/tmp/energy-trading-pipeline-uv-cache` because the default uv cache is outside the workspace sandbox.

### Completion Notes

- Added importable, dependency-free ENTSO-E and Open-Meteo client interfaces with explicit configuration state.
- Unconfigured fetches now log clear skip and local cached-file fallback messages and return without network activity.
- Configured fetches raise `NotImplementedError`, preserving the story boundary against accidental live API implementation.
- Added unit coverage for imports, configuration states, fallback messages, local cached loading, and the unimplemented configured boundary.
- Full regression suite passed: 72 tests. Compilation and whitespace validation also passed.

## File List

- `_bmad-output/implementation-artifacts/sprint-2/story-2.4-add-optional-api-adapter-interfaces.md`
- `src/energy_trading_pipeline/data_ingestion/entsoe_client.py`
- `src/energy_trading_pipeline/data_ingestion/open_meteo_client.py`
- `tests/unit/test_api_adapters.py`

## Change Log

- 2026-07-13: Added optional API adapter interfaces with explicit local-cache fallback behavior and unit coverage; status set to review.

## QA Checklist

- [ ] Story scope matches the approved `epics.md` entry.
- [ ] Acceptance criteria are satisfied.
- [ ] Required tests are added or updated.
- [ ] Tests pass on fixture/debug data where applicable.
- [ ] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [ ] No secrets, tokens, credentials, or large generated datasets were committed.
- [ ] Documentation or configuration was updated if this story changes usage or commands.
