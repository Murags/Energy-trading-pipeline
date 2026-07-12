---
story_id: "1.2"
title: "Define Dependency and Environment Files"
status: "Ready for Dev"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
---

# Story 1.2: Define Dependency and Environment Files

## Status

Ready for Dev

## Parent Epic

Epic 1: Project Setup and Configuration Foundation

## Priority

P0

## Suggested Sprint

Sprint 1

## User Story

As a developer, I want dependency and environment files so that the project can be installed reproducibly in a local Python environment.

## Description

Add `pyproject.toml`, `uv.lock`, `.env.example`, and initial dependency groups for core, dashboard, test, and optional AWS tooling, managed with `uv`.

## Acceptance Criteria

Python 3.11+ is declared, core dependencies include pandas, NumPy, scikit-learn, XGBoost, PyArrow, Matplotlib/Plotly, PyYAML, pytest; `uv.lock` is committed and in sync with `pyproject.toml`; `.env.example` contains placeholder ENTSO-E and AWS variables only; no secrets are committed.

## Technical Notes

Pin or constrain versions during implementation setup using `uv add`/`uv lock`; keep AWS dependencies optional. Do not introduce a `requirements.txt` — `pyproject.toml` plus `uv.lock` is the canonical dependency source (see `AGENTS.md` Dependency Management Rules).

## Files / Modules Likely Affected

`pyproject.toml`, `uv.lock`, `.env.example`.

## Testing Requirements

Create a smoke test that imports the package after dependency installation.

## Dependencies

Story 1.1.

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
