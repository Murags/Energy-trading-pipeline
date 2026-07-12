---
story_id: "10.4"
title: "Add Optional Docker Compose for Dashboard"
status: "Ready for Dev"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P2"
suggested_sprint: "Sprint 10"
source: "_bmad-output/epics.md"
---

# Story 10.4: Add Optional Docker Compose for Dashboard

## Status

Ready for Dev

## Parent Epic

Epic 10: Docker, GitHub Actions, and Reproducibility Support

## Priority

P2

## Suggested Sprint

Sprint 10

## User Story

As an analyst, I want optional Docker Compose support so that the Streamlit dashboard can be launched reproducibly.

## Description

Add optional `docker-compose.yml` for dashboard execution against mounted/exported artifacts.

## Acceptance Criteria

Compose file can run the Streamlit dashboard, dashboard reads mounted `reports/dashboard_exports/`, compose is documented as optional, no AWS or API credentials are required.

## Technical Notes

Only add after dashboard artifact contract is stable.

## Files / Modules Likely Affected

`docker-compose.yml`, `src/energy_trading_pipeline/dashboard/app.py`, `README.md`.

## Testing Requirements

Manual smoke command documented; optional CI check if cheap.

## Dependencies

Story 9.2 and Story 10.3.

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
