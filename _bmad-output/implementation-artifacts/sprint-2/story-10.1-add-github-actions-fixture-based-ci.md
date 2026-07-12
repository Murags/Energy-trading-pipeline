---
story_id: "10.1"
title: "Add GitHub Actions Fixture-Based CI"
status: "review"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P1"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
baseline_commit: "b8ee450f4dfb29b9c4574e552457876b49ac19d6"
---

# Story 10.1: Add GitHub Actions Fixture-Based CI

## Status

Review

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

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Implementation Plan

- Add a static workflow contract test covering triggers, dependency installation,
  fixture-safe pytest execution, and credential-free operation.
- Add the smallest GitHub Actions workflow that installs the locked core and test
  dependencies with `uv` and runs the current pytest suite.
- Run the workflow contract test and full regression suite, then record the
  verified results.

### Debug Log

- Confirmed the new workflow contract test failed before implementation because
  `.github/workflows/ci.yml` did not exist.
- Ran `UV_CACHE_DIR=/tmp/uv-cache uv sync --extra test --locked`; 70 locked
  packages resolved successfully.
- Ran the focused workflow contract test after implementation: 1 passed.
- Ran the full regression suite: 73 passed in 1.70 seconds.
- Ran `git diff --check`, verified the workflow is not ignored, and confirmed no
  credential variables, full-history date range, or backtest command appears in CI.

### Completion Notes

- Added CI for pushes and pull requests on Python 3.11 using the committed
  `uv.lock` and the project `test` dependency group.
- CI runs the current lightweight pytest suite without ENTSO-E/AWS credentials
  and without invoking a historical backtest.
- Added a static workflow contract test to guard CI triggers, setup actions,
  install/test commands, and fixture-safe scope.
- Narrowed `.gitignore` so the CI workflow is committed while existing local
  `.github/agents/` files remain ignored.

## File List

- `.github/workflows/ci.yml` (added)
- `.gitignore` (modified)
- `tests/unit/test_ci_workflow.py` (added)
- `_bmad-output/implementation-artifacts/sprint-2/story-10.1-add-github-actions-fixture-based-ci.md` (modified)

## Change Log

- 2026-07-13: Added fixture-based GitHub Actions CI, workflow contract coverage,
  and the narrow ignore exception required to track the workflow.
