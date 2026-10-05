---
story_id: "10.3"
title: "Add Dockerfile for Reproducible Execution"
status: "review"
baseline_commit: "14d378950ed734d45a6ce449e4ba393e1b7c798e"
parent_epic: "Epic 10: Docker, GitHub Actions, and Reproducibility Support"
priority: "P2"
suggested_sprint: "Sprint 9"
source: "_bmad-output/epics.md"
---

# Story 10.3: Add Dockerfile for Reproducible Execution

## Status

review

## Parent Epic

Epic 10: Docker, GitHub Actions, and Reproducibility Support

## Priority

P2

## Suggested Sprint

Sprint 9

## User Story

As a researcher, I want a Docker image so that the pipeline can run in a reproducible environment after local setup works.

## Description

Add Dockerfile that installs dependencies and supports running tests and CLI commands.

## Acceptance Criteria

Docker build succeeds, container can run pytest against fixtures, container can run a CLI config smoke command, local virtualenv workflow remains documented and primary.

## Technical Notes

Docker must not become required for development.

## Files / Modules Likely Affected

`Dockerfile`, `.dockerignore`, `README.md`.

## Testing Requirements

Manual or CI-optional Docker build/test command documented.

## Tasks/Subtasks

- [x] Add a Dockerfile and .dockerignore that install locked core/test dependencies and include only source, configuration, and fixture-test inputs.
- [x] Document optional Docker build, fixture-test, and CLI smoke commands while keeping the local uv virtualenv workflow primary.
- [x] Verify Docker build, offline container tests, CLI config smoke, and the local regression suite; record results.

## Dependencies

Story 1.4 and enough tests from earlier epics.

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

- 2026-10-05: Workflow resolver requires Python 3.11+; loaded customization defaults manually. No overrides, project context, or sprint status file exist.
- 2026-10-05: User approved adding scope-matched Tasks/Subtasks and completion-record sections.
- Implementation plan: Install locked core/test dependencies with uv in a Python 3.11 image, keep generated artifacts and credentials out of the build context, and run existing offline tests and the config-only CLI without changing pipeline logic.
- Manual acceptance checks: `docker build -t energy-trading-pipeline:local .`; `docker run --rm --network none energy-trading-pipeline:local pytest`; `docker run --rm --network none energy-trading-pipeline:local python -m energy_trading_pipeline.cli --config configs/experiment.yaml`.
- Red/green check: Docker build initially failed because Dockerfile was absent; the implemented image builds successfully. Replaced an older flagged base with digest-pinned Python 3.11.17 on Debian Trixie and removed unused base packaging tools and dependency caches without changing project dependencies.
- Container regression: `docker run --rm --network none energy-trading-pipeline:local pytest -q -rs` passed 1,209 tests; five Streamlit tests skipped because the optional dashboard extra is not installed.
- CLI checks: explicit config-only invocation and the default container command both exited successfully offline and wrote metadata under `/app/logs/runs/run_*/`.
- Local regression: `uv run --no-sync pytest -q` passed all 1,214 tests without modifying installed extras.
- Security caveat: Trivy is unavailable. The OSV container scan reports 4 critical and 33 high vulnerabilities before and after packaging-tool/cache removal; it returns only aggregate counts. Base-image editor diagnostics report six high vulnerabilities. These are unresolved scan warnings, not evidence of a security-clean image; no project dependency changes or production deployment are included in this story.
- Documentation red/green check: the missing optional Docker section failed before editing; documented local-first setup and all three manual acceptance commands passed after editing. Existing README/export contract tests passed (49 tests). Final README-inclusive build and local regression passed (1,214 tests); README diagnostics and whitespace checks are clean.
- Final-image acceptance: Docker build succeeded on linux/arm64; offline container regression passed 1,209 tests with five optional Streamlit skips. Verified CLI exit code 0, the generated run ID/config/model metadata, and exclusion of real data, models, reports, Git history, environment files, and BMAD files from the image.
- Final Docker Scout scan: five fixable critical/high findings remain across three packages, down from seven before removing unused packaging tools/caches. Reported IDs: CVE-2026-25800, GHSA-4w2j-m93h-cj5j, RUSTSEC-2026-0194, RUSTSEC-2026-0195, and CVE-2026-103111. Security remediation beyond this local reproducibility story requires follow-up; no security-clean or production-readiness claim is made.
- Final workflow gate: full local regression passed (1,214 tests), all three tasks are complete, all four changed files are listed, protected story sections are unchanged, and `git diff --check` passed. Corrected the one-off completion validator heading parser before rerunning it successfully. No sprint status file exists; tracking is in this story only.

### Completion Notes

- Implemented only Story 10.3: digest-pinned Python 3.11 image, version-pinned uv, locked core/test dependency installation, XGBoost OpenMP runtime, fixture-safe default tests, and a config-only default CLI command.
- The allowlisted Docker context excludes credentials, local environments, real datasets, and generated artifacts; existing CI/notebook files are included only because fixture tests read them. Unused base packaging tools and dependency caches are not retained.
- README documents the primary local uv virtualenv workflow, optional Docker build/test/CLI commands, optional Streamlit skips, and explicit log mounting. No Compose, dashboard execution, AWS, pipeline logic, dependency metadata, or lockfile changes were introduced.
- Manual acceptance checks were added and exercised; no new pytest files were needed for this infrastructure-only story. Local regression: 1,214 passed. Final container regression: 1,209 passed, five optional dashboard tests skipped. Docker build and offline CLI metadata checks passed.
- All implementation acceptance criteria and workflow completion checks passed; story is ready for review. Security scan warnings remain unresolved and require separate review before any production use. No standalone lint/typecheck command is configured.

## File List

- `Dockerfile`
- `.dockerignore`
- `README.md`
- `_bmad-output/implementation-artifacts/sprint-9/story-10.3-add-dockerfile-for-reproducible-execution.md`

## Change Log

- 2026-10-05: Started Story 10.3 and added user-approved task tracking derived from the existing acceptance criteria.
- 2026-10-05: Added and verified optional Docker execution, allowlisted image inputs, and local-first setup/acceptance documentation; recorded actual regression results and unresolved security scan caveats.
- 2026-10-05: Passed final regression and story-integrity checks; set story status to review.
