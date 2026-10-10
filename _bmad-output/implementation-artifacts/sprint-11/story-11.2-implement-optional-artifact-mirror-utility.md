---
story_id: "11.2"
title: "Implement Optional Artifact Mirror Utility"
status: "review"
baseline_commit: 14fde51eb9c4a89cc71e671cbfab54bb3c08a38d
parent_epic: "Epic 11: Optional AWS Artifact Mirroring"
priority: "P2"
suggested_sprint: "Sprint 11"
source: "_bmad-output/epics.md"
---

# Story 11.2: Implement Optional Artifact Mirror Utility

## Status

review

## Parent Epic

Epic 11: Optional AWS Artifact Mirroring

## Priority

P2

## Suggested Sprint

Sprint 11

## User Story

As a developer, I want an optional artifact mirroring utility so that selected local outputs can be copied to S3 when credentials are available.

## Description

Add utility or script that uploads selected report/log/model artifacts to configured S3 prefixes.

## Acceptance Criteria

Utility is disabled unless AWS config is present, missing credentials produce a clear skip message, local runs are unaffected, mirrored paths match local artifact layout.

## Technical Notes

Mark AWS tests separately and mock S3 interactions.

## Files / Modules Likely Affected

`src/energy_trading_pipeline/utils/io.py`, optional `src/energy_trading_pipeline/utils/aws.py`, `configs/experiment.yaml`.

## Testing Requirements

Unit tests use mocks and are marked to avoid real AWS calls.

## Dependencies

Story 11.1.

## Tasks/Subtasks

- [x] Implement opt-in artifact mirroring with configured S3 prefixes and clear skip messages.
  - [x] Write failing mocked tests before implementing the utility.
  - [x] Upload explicitly selected files while retaining nested local artifact paths.
  - [x] Skip disabled/unconfigured AWS, missing SDK, and missing credentials clearly; isolate optional failures from local execution.
- [x] Add AWS-marked mocked tests for uploads, credentials, path preservation, and local-run isolation.
  - [x] Cover invalid selections/configuration and upload failures without real AWS calls.
- [x] Document usage, run regression checks, and update story records for review.
  - [x] Document disabled defaults, configuration, explicit invocation, and credential-free test commands.
  - [x] Verify acceptance criteria, run regressions, and record all changed files and results.

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

- Used manual customization resolution because system Python lacks `tomllib`; no overrides, project context, or sprint-status file exists.
- User approved adding the missing Tasks/Subtasks section derived from the acceptance criteria. Story 11.1 is implemented and available with status `review`. Worktree was clean at the recorded baseline.
- Red phase: `uv run pytest -q tests/unit/test_aws.py -m aws` failed at collection because the utility did not exist. Initial green phase: 29 mocked tests passed; expanded credential/transfer coverage: 31 passed.
- Added an unmarked offline integration regression proving enabled AWS configuration does not require boto3 or botocore for local CLI metadata generation. All AWS tests replace SDK interactions and run without the AWS extra installed.
- Validation: `uv run pytest -q tests/unit/test_aws.py -m aws` -> 31 passed. `uv run pytest -q` -> 1221 passed, 31 deselected. After a small result-handling refactor, both commands passed again with the same counts.
- `git diff --check` passed. No standalone lint/typecheck tool is configured in `pyproject.toml`. No dependency or lockfile changes were necessary; no AWS calls or historical experiments were run.
- Definition-of-done review confirmed scope, acceptance criteria, completed task checkboxes, seven-file inventory, documentation, and preserved protected story sections. Original QA Checklist remains untouched per workflow edit restrictions; its conditions are evidenced here. Workflow completion customization resolves to an empty value.

### Completion Notes

- Implementation plan: provide a standalone utility in `utils/aws.py`, lazily load the existing optional AWS extra, and mirror explicitly selected files using configured local-root-to-S3-prefix mappings. Local pipeline stages do not invoke AWS. Validate configuration/selections before uploads, report optional AWS failures clearly, and verify with mocked AWS tests and offline regressions.
- Implemented `mirror_artifacts` and immutable `MirrorResult`. Explicit selections preserve run/model/report suffixes beneath configurable prefixes, including external local roots. All selections are validated before AWS access; ambiguous mappings, duplicate keys, invalid prefixes, and missing/non-file inputs fail clearly.
- Disabled/absent configuration, absent SDK, empty selection, and unavailable/incomplete credentials skip clearly. SDK initialization failures skip; managed-transfer/service/transport upload failures are logged and returned while other files continue. Completed uploads and failures remain recorded if credentials disappear mid-copy. Local files are never mutated.
- Added disabled sample AWS configuration and documented optional setup, standard credential-chain use, permissions, Python invocation, mapping behavior, result interpretation, and credential-free test selection. No local execution hooks were introduced.
- Added 31 AWS-marked mocked unit tests and one offline CLI integration test. All acceptance criteria pass and no blockers remain. Story is ready for independent code review; no sprint-status file exists.

## File List

- `_bmad-output/implementation-artifacts/sprint-11/story-11.2-implement-optional-artifact-mirror-utility.md` (modified)
- `src/energy_trading_pipeline/utils/aws.py` (added)
- `tests/unit/test_aws.py` (added)
- `tests/integration/test_cli_entry_point.py` (modified)
- `configs/experiment.yaml` (modified)
- `docs/artifact_mirroring.md` (added)
- `README.md` (modified)

## Change Log

- 2026-10-10: Added user-approved tasks, captured baseline, and started Story 11.2.
- 2026-10-10: Implemented optional selected-file S3 mirroring, disabled configuration defaults, usage documentation, and mocked AWS/local-isolation tests. Passed 31 AWS unit tests, 1221 offline regressions, and whitespace checks; marked story `review`.
