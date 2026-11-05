---
title: 'Run the day-ahead forecast daily on AWS, with an on-demand dashboard'
type: 'feature'
created: '2026-11-03'
status: 'in-progress'
baseline_commit: '6f0c0a0'
context:
  - 'AGENTS.md'
  - 'docs/CODING_STYLE.md'
  - 'docs/artifact_mirroring.md'
  - '_bmad-output/implementation-artifacts/spec-day-ahead-availability.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The pipeline only replays history. There is no way to issue a genuine forecast for the next delivery day, nor to show the pipeline operating for the defense.

**Approach:** Package the existing feature, availability, model and retraining code as a daily batch job on AWS Lambda, triggered at 18:15 Europe/Berlin. Each run issues tomorrow's 24-hour forecast for all three strategies, applies each strategy's retraining policy to live data, and writes forecasts, model versions and events to S3. The dashboard reads those artifacts from S3 and runs on ECS Fargate only when started on demand. Backtests remain local.

## Boundaries & Constraints

**Always:** Follow the AGENTS.md AWS rules: S3, Lambda/EventBridge, CloudWatch and Terraform only. Keep local execution fully functional without AWS. Use the same predictors, model parameters, availability contract and 18:00 issuance as the backtested model. Run all three canonical strategies, each with its own model lineage. Use IAM roles, never stored credentials. Create a budget alert.

**Never:** Always-on compute; SageMaker, Airflow, Kubernetes or Spark; cloud backtesting; credentials in code, config or the image; a live model whose features or parameters differ from the backtested one; a forecast using any predictor not yet published at issuance.

**Ask First:** Any `terraform apply`. Dropping or replacing a predictor (see filter 122 below). Keeping the dashboard running between sessions.

**Open item:** SMARD filter 122 (`forecast_generation_total_de`) had not covered the next delivery day at 19:46 Berlin on 2026-10-22, while filter 5097 had. Publication times are being measured (`logs/smard_publication_watch/`). If 122 is not reliably published by issuance, the live job cannot use it, and the predictor list must change for both live and backtest.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Normal daily run | 18:15 Berlin, all inputs published | 24 forecast rows per strategy for tomorrow; actuals filled for earlier days | None |
| Predictor not yet published | Tomorrow's forecast series incomplete | No forecast written for that strategy-day | Fail clearly, logged; prior state untouched |
| SMARD unavailable | HTTP errors | No partial writes | Retry with backoff, then fail logged |
| Run repeated same day | Lambda retry or manual re-run | Same delivery day overwritten, never duplicated | Idempotent by delivery date |
| Policy requests refit | Live forecast history crosses rule | New versioned model in S3, event logged | Model write precedes forecast write |
| First run | Empty state | Initial fit on last 90 days per strategy | Bootstrap path, logged |

</frozen-after-approval>

## Code Map

- `data_ingestion/smard_client.py` — new: fetch SMARD hourly series for a half-open UTC interval; replaces the lost one-off acquisition scripts.
- `forecasting/` (new module) — daily issuance: load state, update data, backfill actuals, apply policy, predict, persist.
- `forecasting/state.py` — artifact store over a local directory or S3 prefix, one interface.
- `cli.py` — `forecast-next-day` command.
- `deploy/lambda/` — Lambda handler and container image.
- `dashboard/` — load exports from S3 at start-up; Live tab.
- `infrastructure/terraform/` — ECR, Lambda, EventBridge Scheduler, IAM, CloudWatch, ECS task, budget.
- `docs/deployment.md` — defense runbook.

## Tasks & Acceptance

**Execution:**
- [ ] SMARD client with fixture-backed unit tests and one `external_api` live test.
- [ ] Forecasting module and `forecast-next-day` CLI, runnable locally against a directory store.
- [ ] S3-backed store, tested with a local fake; one `aws`-marked live test.
- [ ] Lambda handler and image, verified locally with the Lambda runtime emulator.
- [x] Dashboard S3 loading and Live tab.
- [x] Terraform additions, reviewed with `terraform plan` before any apply.
- [ ] Defense runbook.

**Acceptance Criteria:**
- Given a local directory store, when `forecast-next-day` runs, then each strategy writes 24 rows for the next local delivery day using only data available at 18:00 Berlin.
- Given a repeated run for the same day, then no forecast row is duplicated.
- Given CI, then no test requires network, AWS credentials or SMARD.
- Given the deployed stack, when the Lambda is invoked, then forecasts appear in S3 and in the dashboard's Live tab.
- Given the dashboard is stopped, then no compute is billed.

## Verification

- `uv run pytest` (default markers), then the `external_api` and `aws` tests explicitly.
- Local Lambda image run through the runtime emulator.
- `terraform plan` reviewed by the user before `apply`.
