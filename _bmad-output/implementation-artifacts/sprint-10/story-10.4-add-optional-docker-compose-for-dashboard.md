---
story_id: "10.4"
title: "Add Optional Docker Compose for Dashboard"
status: "review"
baseline_commit: "c78e4c4a6972d8edd934b7e18d371bed80b38955"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P2"
suggested_sprint: "Sprint 10"
source: "_bmad-output/epics.md"
---

# Story 10.4: Add Optional Docker Compose for Dashboard

## Status

review

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

## Tasks/Subtasks

- [x] Add optional Compose dashboard execution using locked dashboard dependencies and a read-only mount of exported artifacts, without credentials or pipeline execution.
- [x] Document optional Compose startup, artifact prerequisites, manual smoke checks, and shutdown while preserving the primary local workflow.
- [x] Verify Compose configuration, fixture-backed dashboard execution, and the offline regression suite; record results.

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

## Dev Agent Record

### Debug Log

- 2026-10-06: Used the documented manual workflow-resolution fallback because system Python lacks tomllib. No overrides, project context, or sprint-status file exist; English and intermediate skill level loaded from BMM config.
- 2026-10-06: User approved adding scope-derived Tasks/Subtasks. Fresh implementation; dependencies 9.2 and 10.3 are implemented and available at review status.
- Implementation plan: Reuse the Dockerfile with an opt-in dashboard dependency build argument, launch only Streamlit, and bind the existing export directory read-only. Add credential-free configuration checks and document manual startup, health, artifact-read, and shutdown checks.
- Service red/green: Three contract tests failed because Compose was absent, then passed after implementation; Docker Compose config validation and dashboard image build passed.
- Service validation: Local offline suite and network-disabled dashboard image suite both passed 1,217 tests. Compose smoke reused existing fixture helpers in a temporary export directory, rendered five views and three strategies, rejected writes with EROFS, and preserved all four artifact hashes.
- Existing risk: The unchanged base image has six high-vulnerability editor warnings, already recorded in Story 10.3; no security-clean or production-readiness claim is made.
- Documentation red/green: The missing Compose section failed its new contract test, then all 53 focused Compose/export tests passed. Final README-inclusive dashboard build and all 1,218 local offline regressions passed; README, Compose, and test diagnostics are clean.
- Final live smoke: Used a temporary Compose stdin override to mount existing synthetic fixture exports read-only, preserving host research exports. Service reached healthy status on local port 18501; the health endpoint returned ok and the documented artifact-read command loaded 12 forecasts, three metrics, one event, and two model versions. Streamlit AppTest verified five views, three strategies, and a clear missing-export state. Shutdown removed the service/network; fixture hashes stayed unchanged and temporary files were removed.
- Final-image regression: Dashboard image passed all 1,218 tests with network disabled. Default core/test image built successfully and passed 1,213 offline tests with five expected optional Streamlit skips; its unchanged default CLI smoke command exited successfully and wrote container-local metadata.
- No standalone lint/typecheck command is configured. Four new offline contract tests are automatically included by existing pytest/CI discovery; no Docker daemon or network is needed for those tests.
- Completion gates: Full local regression rerun passed all 1,218 tests; whitespace and story-integrity checks passed. Verified three completed tasks, all six changed files listed, unchanged protected story sections/frontmatter, no sprint tracking, and no remaining Compose service. Corrected the one-off integrity validator to ignore section-separator blank lines before it passed.

### Completion Notes

- Optional Compose service implemented and verified. Default Docker builds still select core/test dependencies and retain the config-only CLI command; Compose opts into the existing locked dashboard extra. No dashboard application, pipeline, dependency metadata, or lockfile changes were needed.
- README documents optional startup, all four snapshot prerequisites, health and artifact-read smoke commands, the local-only port override, missing-export behavior, and shutdown without deleting host exports. Local uv execution remains primary.
- Added four credential-free tests covering optional build selection, Streamlit-only startup/health, local port binding, the read-only export mount, absence of credential/service dependencies, and optional usage documentation. Actual Docker build, mounted-fixture rendering, missing exports, port publishing, startup/shutdown, and offline regression checks passed.
- All three approved tasks and definition-of-done gates are complete; Story 10.4 is ready for review. No generated research artifacts, credentials, app behavior changes, new dependencies, future stories, or cloud operations were introduced. The original QA Checklist remains unchanged under the story-edit restrictions; its requirements are evidenced by these checks.
- No implementation blockers remain. Existing base-image vulnerability warnings remain outside this story's scope. The smoke service and temporary fixtures were cleaned up; launch against an existing research snapshot using the documented command. Recommended next step: independent code review.

## File List

- `docker-compose.yml`
- `Dockerfile`
- `.dockerignore`
- `README.md`
- `tests/unit/test_docker_compose.py`
- `_bmad-output/implementation-artifacts/sprint-10/story-10.4-add-optional-docker-compose-for-dashboard.md`

## Change Log

- 2026-10-06: Added user-approved scoped task tracking, captured baseline, and started Story 10.4.
- 2026-10-06: Added optional artifact-only Compose support, opt-in locked dashboard dependencies, four offline contract tests, and local-first usage/smoke documentation; verified both image variants and temporary-fixture startup, artifact access, and shutdown.
- 2026-10-06: Passed final regression and definition-of-done checks; set Story 10.4 status to review.
