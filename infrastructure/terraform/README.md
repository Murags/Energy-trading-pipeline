# Optional AWS Daily Forecast Stack

This Terraform root defines the optional AWS demonstration environment.
No AWS resources or credentials are required for local pipeline runs, tests,
backtests, or the local dashboard. Terraform is never invoked by the Python pipeline.

The stack contains:

- a private, encrypted, versioned S3 artifact bucket;
- immutable, scan-on-push ECR repositories for the forecast and dashboard;
- a container-image Lambda with least-privilege S3 and CloudWatch access;
- an EventBridge Scheduler trigger at **18:15 `Europe/Berlin`** (DST-aware);
- explicit 14-day CloudWatch log groups;
- an ECS cluster and Fargate task definition for a manually started dashboard;
- a small public VPC with dashboard ingress restricted to one configured CIDR;
- forecasted-80% and actual-100% monthly AWS Budget email notifications.

There is no ECS service, load balancer, NAT gateway, database, or always-on
compute. The dashboard task is billed only while someone explicitly runs it.
Terraform does not start a dashboard task.

## Required Inputs

Use an ignored `terraform.tfvars` file or `TF_VAR_...` environment variables.
Never commit personal email addresses, account details, or Terraform state.

```hcl
bucket_name              = "energy-pipeline-artifacts-unique-suffix"
budget_notification_email = "researcher@example.com"
dashboard_allowed_cidr    = "198.51.100.10/32"
budget_limit_usd          = 10
```

`dashboard_allowed_cidr` should normally be the reviewer's current public IPv4
address with `/32`. `0.0.0.0/0` is rejected. The budget covers the whole AWS
account, not only tagged resources, so unrelated account usage can trigger it.
Budget notifications require email confirmation when AWS requests it.

Important optional variables include `aws_region` (`eu-central-1`),
`lambda_memory_mb` (4096), `lambda_timeout_seconds` (900),
`log_retention_days` (14), and the two immutable image tags. The schedule is
enabled by default and can be staged disabled with `schedule_enabled = false`.

## Two-Stage Deployment

Lambda validates that its ECR image exists when the function is created. Since
this stack also creates the ECR repositories, a clean account requires two
separately reviewed plans. This avoids a partial first apply.

### 1. Bootstrap storage and repositories

Leave the default:

```hcl
deploy_workloads = false
```

Then initialize, validate, and save a bootstrap plan:

```sh
terraform -chdir=infrastructure/terraform init -input=false
terraform -chdir=infrastructure/terraform fmt -check
terraform -chdir=infrastructure/terraform validate
terraform -chdir=infrastructure/terraform plan -out=bootstrap.tfplan
terraform -chdir=infrastructure/terraform show bootstrap.tfplan
```

Review costs and resources before any apply. Applying requires explicit human
approval:

```sh
terraform -chdir=infrastructure/terraform apply bootstrap.tfplan
```

The bootstrap creates the ECR repositories and supporting non-workload
resources, but no Lambda, schedule, or dashboard task definition.

### 2. Push images and enable workloads

After an approved bootstrap apply, authenticate Docker and use immutable tags,
for example the short Git commit SHA. Build for `linux/amd64`, matching Lambda
and Fargate:

```sh
account_id=$(aws sts get-caller-identity --query Account --output text)
region=$(terraform -chdir=infrastructure/terraform output -raw aws_region)
registry="$account_id.dkr.ecr.$region.amazonaws.com"
aws ecr get-login-password --region "$region" | docker login --username AWS --password-stdin "$registry"

tag=$(git rev-parse --short HEAD)
forecast_repo=$(terraform -chdir=infrastructure/terraform output -raw forecast_repository_url)
dashboard_repo=$(terraform -chdir=infrastructure/terraform output -raw dashboard_repository_url)

docker buildx build --platform linux/amd64 --provenance=false --sbom=false \
  -f deploy/lambda/Dockerfile -t "$forecast_repo:$tag" --push .
docker buildx build --platform linux/amd64 -f deploy/dashboard/Dockerfile -t "$dashboard_repo:$tag" --push .
```

Set `deploy_workloads = true`, set both image tags to that immutable tag, and
create a second reviewed plan:

```hcl
deploy_workloads    = true
lambda_image_tag    = "<git-sha>"
dashboard_image_tag = "<git-sha>"
```

```sh
terraform -chdir=infrastructure/terraform plan -out=workloads.tfplan
terraform -chdir=infrastructure/terraform show workloads.tfplan
```

Do not apply without explicit approval. The schedule uses
`cron(15 18 * * ? *)` with `Europe/Berlin`; it therefore remains at 18:15 local
time across daylight-saving changes.

## On-Demand Dashboard

After the dashboard S3/Live-tab implementation and an approved workload apply,
start one task manually. No service keeps it alive or restarts it:

```sh
cluster=$(terraform -chdir=infrastructure/terraform output -raw dashboard_cluster_name)
task_definition=$(terraform -chdir=infrastructure/terraform output -raw dashboard_task_definition_arn)
subnet=$(terraform -chdir=infrastructure/terraform output -raw dashboard_subnet_id)
security_group=$(terraform -chdir=infrastructure/terraform output -raw dashboard_security_group_id)

aws ecs run-task --cluster "$cluster" --task-definition "$task_definition" \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[$subnet],securityGroups=[$security_group],assignPublicIp=ENABLED}"
```

Read the task's public IP from its attached ENI and open port 8501. Stop the
task immediately after review to stop Fargate and public-IPv4 charges:

```sh
aws ecs list-tasks --cluster "$cluster"
aws ecs stop-task --cluster "$cluster" --task <task-arn>
```

Keeping the dashboard running between sessions requires explicit approval.
The prototype endpoint is CIDR-restricted but does not terminate TLS or provide
application authentication. Use it only from the configured trusted IP for a
short review session; do not expose sensitive data or broaden the CIDR.

The task derives its read-only historical export location as
`$ETP_STORE/reports/dashboard_exports`. Upload all four files listed below before
starting the task; the Backtest tab never runs a backtest or writes artifacts.
The task also sets `ARROW_DEFAULT_MEMORY_POOL=system` to avoid native allocator
crashes while filtering larger Parquet exports.

## Artifact Layout

Repository-relative paths remain the S3 object keys. The live forecast uses
`market/` and `live/<strategy>/`; existing mirrored outputs retain these paths:

| Local directory | S3 prefix | Contents |
| --- | --- | --- |
| `data/raw/` | `data/raw/` | Optional cached source data. |
| `data/processed/` | `data/processed/` | Processed datasets and metadata. |
| `data/features/` | `data/features/` | Feature datasets and metadata. |
| `models/` | `models/` | Versioned models and registry artifacts. |
| `logs/` | `logs/` | Run, forecast, error, and retraining logs. |
| `reports/tables/` | `reports/tables/` | Evaluation tables. |
| `reports/figures/` | `reports/figures/` | Evaluation figures. |
| `reports/dashboard_exports/` | `reports/dashboard_exports/` | Dashboard snapshots. |

The existing dashboard exports keep their exact keys:

```text
reports/dashboard_exports/forecasts.parquet
reports/dashboard_exports/metrics.parquet
reports/dashboard_exports/retraining_events.parquet
reports/dashboard_exports/model_versions.parquet
```

## Credential-Free Verification

Initialization downloads the AWS provider but does not create resources:

```sh
terraform -chdir=infrastructure/terraform init -backend=false -input=false
terraform -chdir=infrastructure/terraform fmt -check
terraform fmt -check tests/unit/terraform_s3.tftest.hcl
terraform -chdir=infrastructure/terraform validate
```

The native test uses a mock AWS provider. Terraform expects tests beneath the
configuration root, so copy the configuration and test into a temporary folder:

```sh
test_root=$(mktemp -d)
cp infrastructure/terraform/*.tf infrastructure/terraform/README.md \
  infrastructure/terraform/.terraform.lock.hcl "$test_root/"
mkdir "$test_root/tests"
cp tests/unit/terraform_s3.tftest.hcl "$test_root/tests/"
terraform -chdir="$test_root" init -backend=false -input=false -lockfile=readonly \
  -plugin-dir="$PWD/infrastructure/terraform/.terraform/providers"
terraform -chdir="$test_root" test
```

The mock tests require no AWS credentials and create nothing. The default Python
suite also remains offline: `uv run pytest -q`.

## Security and Cost Boundaries

- IAM roles use service-specific trust policies and bucket/prefix-scoped S3 access.
- The artifact bucket blocks public access, disables ACLs, encrypts objects, and
  enables versioning. `force_destroy = false` protects nonempty ECR repositories
  and the S3 bucket.
- Dashboard ingress rejects public `0.0.0.0/0`; outbound access is HTTPS only.
- No secrets or AWS credentials enter an image, variable, or source file.
- S3, ECR, and CloudWatch charge for stored bytes; Lambda and Scheduler charge
  per use after applicable free tiers. Fargate CPU/memory and a public IPv4
  address are charged only while a dashboard task runs.
- AWS Budgets can itself incur a small charge after the account's free budget
  allowance. A budget alerts but does not automatically stop resources.
- There is no NAT gateway or load balancer, avoiding their hourly charges.

Terraform uses local state. Keep state and saved plans private and backed up;
`.gitignore` excludes them. Empty versioned objects and ECR images before
destroying because destructive deletion is intentionally disabled.

## Cleanup

Always review the destroy plan with the same variables and state:

First list and stop any dashboard task, then wait until ECS reports it stopped.
Terraform cannot reliably delete the cluster or networking around an unmanaged
running task.

```sh
terraform -chdir=infrastructure/terraform plan -destroy -out=destroy.tfplan
terraform -chdir=infrastructure/terraform show destroy.tfplan
terraform -chdir=infrastructure/terraform apply destroy.tfplan
```

Do not run destroy without explicit approval. Terraform cannot delete nonempty
repositories or the nonempty versioned bucket while `force_destroy = false`.
