---
story_id: "9.3"
title: "Document Dashboard Fallback Path"
status: "Ready for Dev"
parent_epic: "Epic 9: Dashboard Reading Exported Artifacts Only"
priority: "P2"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 9.3: Document Dashboard Fallback Path

## Status

Ready for Dev

## Parent Epic

Epic 9: Dashboard Reading Exported Artifacts Only

## Priority

P2

## Suggested Sprint

Sprint 9

## User Story

As a researcher, I want a notebook/static report fallback so that the project remains deliverable if dashboard polish is constrained.

## Description

Document how to inspect exported artifacts through notebook or static report outputs if Streamlit is unavailable.

## Acceptance Criteria

README or docs describe Streamlit command, required export files, and fallback notebook/static report path; fallback does not require rerunning the full backtest.

## Technical Notes

This supports the PRD boundary that dashboard should not block core MVP.

## Files / Modules Likely Affected

`README.md`, `notebooks/03_backtest_review.ipynb`, `notebooks/04_report_figures.ipynb`, `docs/`.

## Testing Requirements

Documentation review; optional notebook smoke run on fixture artifacts.

## Dependencies

Story 9.2.

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
