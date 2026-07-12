---
story_id: "2.1"
title: "Implement Local CSV and Parquet Loader"
status: "Ready for Dev"
parent_epic: "Epic 2: Local Data Loading and Artifact Handling"
priority: "P0"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
---

# Story 2.1: Implement Local CSV and Parquet Loader

## Status

Ready for Dev

## Parent Epic

Epic 2: Local Data Loading and Artifact Handling

## Priority

P0

## Suggested Sprint

Sprint 2

## User Story

As a researcher, I want to load local CSV/Parquet files so that experiments can run without API access.

## Description

Implement reusable local loading functions for configured dataset paths and supported file formats.

## Acceptance Criteria

Loader reads CSV and Parquet, returns pandas DataFrames, validates file existence, logs source path and row count, raises clear errors for unsupported formats.

## Technical Notes

Keep local loading independent of ENTSO-E/Open-Meteo clients.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/data_ingestion/local_loader.py`, `src/energy_trading_pipeline/utils/io.py`.

## Testing Requirements

Unit tests load sample CSV and sample Parquet fixture data.

## Dependencies

Story 1.3.

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
