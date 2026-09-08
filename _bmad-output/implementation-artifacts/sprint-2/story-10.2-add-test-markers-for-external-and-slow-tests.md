---
story_id: "10.2"
title: "Add Test Markers for External and Slow Tests"
status: "review"
baseline_commit: "682ce70e8c81e966328df7e0d1a937447c801bff"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P1"
suggested_sprint: "Sprint 2"
source: "_bmad-output/epics.md"
---

# Story 10.2: Add Test Markers for External and Slow Tests

## Status

Review

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

- [x] Story scope matches the approved `epics.md` entry.
- [x] Acceptance criteria are satisfied.
- [x] Required tests are added or updated.
- [x] Tests pass on fixture/debug data where applicable.
- [x] No unintended dashboard, AWS, Docker, API, or modelling scope was added.
- [x] No secrets, tokens, credentials, or large generated datasets were committed.
- [x] Documentation or configuration was updated if this story changes usage or commands.

## Dev Agent Record

### Debug Log

- Confirmed Story 10.1's workflow and test dependency are available. No sprint
  status file or review follow-ups exist; progress is tracked in this story.
- Added six subprocess selection cases and updated the CI contract test first.
  All seven failed before implementation due to missing marker registration and
  the missing CI exclusion expression.
- Registered markers and added default exclusions and strict marker checking.
  Adjusted subprocess verbosity so CI's quiet flag does not hide selected names.
- `uv run --locked --extra test pytest -q`: 79 passed in 4.68 seconds.
- `uv run pytest -q -m "not external_api and not aws and not slow"`: 79 passed
  in 2.07 seconds.
- `git diff --check` passed. No lint/static-analysis tool is configured.
- Local verification used Python 3.14.4; CI remains configured for Python 3.11.
  GitHub-hosted execution was not performed in this session.

### Completion Notes

- Defined `external_api`, `aws`, and `slow` in pytest configuration, with all
  three deselected by default. CI explicitly uses the same exclusion expression.
- Enabled strict marker validation to catch misspelled marker names.
- Verified default selection, CI selection with local defaults disabled,
  individual category opt-ins, and the empty expression that enables all tests.
  Synthetic tests include combined markers and require no external services.
- Kept existing offline adapter tests in the default suite. There are no live
  API/AWS or long-running tests to mark in the current repository.
- Documented marker use, local opt-ins, optional AWS test dependency installation,
  empty selections, and collection-time restrictions for live clients/credentials.
- No dependencies changed; locked execution succeeded with the existing uv.lock.
  No application behavior or future-story features were introduced.

## File List

- `pyproject.toml` (modified)
- `.github/workflows/ci.yml` (modified)
- `README.md` (modified)
- `tests/unit/test_ci_workflow.py` (modified)
- `tests/integration/test_pytest_markers.py` (added)
- `_bmad-output/implementation-artifacts/sprint-2/story-10.2-add-test-markers-for-external-and-slow-tests.md` (modified)

## Change Log

- 2026-09-08: Implemented Story 10.2 with registered pytest markers, default and
  CI exclusions, local opt-in documentation, and behavioral selection tests.
