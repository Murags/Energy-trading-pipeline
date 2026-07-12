---
story_id: "1.2"
title: "Define Dependency and Environment Files"
status: "Ready for Dev"
parent_epic: "Epic 1: Project Setup and Configuration Foundation"
priority: "P0"
suggested_sprint: "Sprint 1"
source: "_bmad-output/epics.md"
baseline_commit: "2b02234ce7dea6b27919191889c7903d141a9ae6"
---

# Story 1.2: Define Dependency and Environment Files

## Status

Review

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

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Debug Log

- Ran `uv lock` to generate `uv.lock` from `pyproject.toml` (70 packages resolved).
- Ran `uv sync --extra dashboard --extra test --extra aws` to install all dependency groups locally.
- Ran `uv run pytest -q`; initial run failed on `xgboost` import (`libomp.dylib` not found, a local macOS OpenMP runtime gap unrelated to the dependency declarations). Installed `libomp` via Homebrew; re-ran suite and all tests passed.

### Completion Notes

- Added `dependencies` (core) and `[project.optional-dependencies]` groups (`dashboard`, `test`, `aws`) to `pyproject.toml`, matching the allowed dependency list in `docs/CODING_STYLE.md`.
- Core group: pandas, numpy, scikit-learn, xgboost, pyarrow, matplotlib, plotly, pyyaml.
- `dashboard` group: streamlit. `test` group: pytest. `aws` group: boto3 (kept optional per architecture and `AGENTS.md` AWS rules).
- Generated and committed `uv.lock`, in sync with `pyproject.toml`.
- Updated `.env.example` with placeholder `ENTSOE_API_KEY` and `AWS_*` variables only; no real credentials.
- Added `.env` to `.gitignore` to prevent accidental secret commits.
- Added `tests/unit/test_dependency_smoke.py` verifying the package and all core third-party dependencies import successfully after installation, per the story's testing requirement.
- Did not introduce `requirements.txt`, disallowed dependencies (SageMaker, Airflow, Kubernetes, Spark, MLflow, Pandera, Great Expectations), or any dashboard/AWS/Docker functional scope beyond the dependency declarations themselves.

## File List

- `pyproject.toml` (modified)
- `uv.lock` (added)
- `.env.example` (modified)
- `.gitignore` (modified)
- `tests/unit/test_dependency_smoke.py` (added)

## Change Log

- 2026-07-12: Implemented Story 1.2 — added core/dashboard/test/aws dependency groups to `pyproject.toml`, generated `uv.lock`, populated `.env.example` with ENTSO-E and AWS placeholders, gitignored `.env`, and added a dependency-installation smoke test.
