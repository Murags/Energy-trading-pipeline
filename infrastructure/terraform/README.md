# Optional S3 Artifact Storage

This Terraform root demonstrates optional artifact storage for Story 11.1.
No AWS resources or credentials are required for local pipeline runs, fixture
tests, backtests, or the dashboard. Local artifacts remain the source of truth.
Nothing in the Python CLI, Docker configuration, or CI invokes Terraform.

The skeleton creates one S3 bucket and three bucket-scoped security controls:
all public access is blocked, default encryption uses S3-managed AES256 keys,
and bucket-owner-enforced ownership disables ACLs. It does not create IAM roles,
KMS keys, remote state storage, cloud compute, objects, or upload automation.
Artifact mirroring is a separate story; applying this skeleton leaves an empty
bucket and does not upload or change local files.

## Inputs and Outputs

Terraform 1.7 or newer (below 2.0) is required. The AWS provider uses version 6.x;
the committed `.terraform.lock.hcl` pins the selected version and checksums.
Terraform is a separate, optional tool, not a Python or local-run dependency.

| Variable | Default | Purpose |
| --- | --- | --- |
| `bucket_name` | Required | Globally unique S3 bucket name. |
| `aws_region` | `eu-central-1` | Region for the optional bucket. |
| `tags` | `{ project = "energy_trading_pipeline" }` | Bucket tags. |

The bucket naming convention is intentionally narrower than S3's full rules:
3-63 lowercase letters or digits, optionally separated by single hyphens.
Dots, underscores, consecutive hyphens, IP-address names, leading/trailing
hyphens, and AWS-reserved prefixes/suffixes are rejected. Terraform cannot check
global name availability without AWS; choose your own unique name.

Outputs are `bucket_name`, `bucket_arn`, `bucket_uri`, `aws_region`, and
`artifact_prefixes`. The last output maps local directories to S3 key prefixes;
it describes the layout but does not create folder objects.

## Mirrored Artifact Layout

Keep each artifact's repository-relative path as its S3 object key. Append it
to `bucket_uri`; do not flatten nested paths or rename run/model identifiers.
The table describes the default local layout. If local directories are
configured elsewhere, preserve these canonical destination prefixes rather
than using an absolute host path as an object key.

| Local directory | S3 prefix | Contents |
| --- | --- | --- |
| `data/raw/` | `data/raw/` | Optional cached source data, including source subdirectories. |
| `data/processed/` | `data/processed/` | Aligned/cleaned datasets and processing-run metadata. |
| `data/features/` | `data/features/` | Feature dataset and metadata. |
| `models/` | `models/` | `artifacts/model_YYYYMMDD_HHMMSS/` and `registry/`. |
| `logs/` | `logs/` | Run metadata, forecasts, actuals, errors, and retraining logs. |
| `reports/tables/` | `reports/tables/` | Metrics, comparisons, and saved result tables. |
| `reports/figures/` | `reports/figures/` | Forecast, rolling RMSE, event, and comparison plots. |
| `reports/dashboard_exports/` | `reports/dashboard_exports/` | The four artifact-only dashboard exports. |

For example, `models/artifacts/model_20260911_153514/model.json` maps to
`s3://<bucket_name>/models/artifacts/model_20260911_153514/model.json`.
`logs/runs/run_20260911_183514/` keeps the same nested run prefix. Model/run
examples illustrate naming only; mirror only artifacts that actually exist.

Story 8.4's exports retain these exact keys:

```text
reports/dashboard_exports/forecasts.parquet
reports/dashboard_exports/metrics.parquet
reports/dashboard_exports/retraining_events.parquet
reports/dashboard_exports/model_versions.parquet
```

The dashboard continues to read local exported artifacts, not this bucket.
Do not mirror credentials, Terraform state/plans, local environment files,
or datasets whose source terms do not permit storage in S3.

## Verify Without AWS

Run these commands from the repository root:

```sh
terraform -chdir=infrastructure/terraform init -backend=false -input=false
terraform -chdir=infrastructure/terraform fmt -check
terraform fmt -check tests/unit/terraform_s3.tftest.hcl
terraform -chdir=infrastructure/terraform validate
```

Initialization downloads the provider from the Terraform registry and needs
network access, but not AWS credentials. Validation does not provision anything.
After initialization, the native tests reuse that provider locally and make no
AWS calls. Terraform requires tests inside its configuration root, so stage
the repository's unit tests and configuration in a temporary test root:

```sh
test_root=$(mktemp -d)
cp infrastructure/terraform/main.tf infrastructure/terraform/variables.tf \
  infrastructure/terraform/outputs.tf infrastructure/terraform/README.md \
  infrastructure/terraform/.terraform.lock.hcl "$test_root/"
mkdir "$test_root/tests"
cp tests/unit/terraform_s3.tftest.hcl "$test_root/tests/"
terraform -chdir="$test_root" init -backend=false -input=false \
  -lockfile=readonly \
  -plugin-dir="$PWD/infrastructure/terraform/.terraform/providers"
terraform -chdir="$test_root" test
```

The test file explicitly mocks the AWS provider, including its `apply` test;
no real bucket is created or deleted. Tests cover security settings, outputs,
invalid bucket names, artifact mappings, and this usage documentation. The
temporary directory can be removed after testing.

The existing offline regression command remains `uv run pytest -q`. Pytest
does not execute `.tftest.hcl` files. CI remains unchanged and requires neither
Terraform, AWS credentials, provider downloads, nor cloud resources.

## Provision Only When Explicitly Needed

Real `plan`, `apply`, and `destroy` commands contact AWS. They require an
existing authenticated AWS profile/role and may incur S3 storage/request
charges. Use your normal AWS credential chain; never put access keys in
Terraform variables, source files, or Git. No IAM policies are provisioned here.

Ask the account administrator for bucket-scoped permissions for the chosen
bucket. Provisioning needs `s3:CreateBucket`, `s3:DeleteBucket`, `s3:ListBucket`,
`s3:GetBucketLocation`, and `s3:GetBucketTagging`/`s3:PutBucketTagging`, plus
read/write permissions for public-access blocking, encryption configuration,
and ownership controls (`s3:GetBucketPublicAccessBlock`,
`s3:PutBucketPublicAccessBlock`, `s3:GetEncryptionConfiguration`,
`s3:PutEncryptionConfiguration`, `s3:GetBucketOwnershipControls`, and
`s3:PutBucketOwnershipControls`). The provider may also need read permissions
for other bucket configuration during refresh; scope those to this bucket
rather than granting account-wide administrator access. Object upload/read
permissions are not needed for this empty-bucket skeleton.

Choose a globally unique name, replace the example profile/name below, and
review the plan before applying:

```sh
export AWS_PROFILE="research-demo"
export TF_VAR_bucket_name="energy-research-artifacts-your-unique-suffix"
export TF_VAR_aws_region="eu-central-1"
terraform -chdir=infrastructure/terraform plan -out=optional_s3.tfplan
terraform -chdir=infrastructure/terraform apply optional_s3.tfplan
terraform -chdir=infrastructure/terraform output
```

Expect only the bucket and its three security controls. Do not apply if the
plan includes unrelated resources. Terraform uses local state by default;
keep that state private and available for subsequent management and cleanup.
Local provider working directories, state/backups, `.tfplan` files, `.tfvars`
files, and crash logs are ignored by Git. Keep the provider lockfile committed.

## Cleanup

```sh
terraform -chdir=infrastructure/terraform destroy
```

Review and confirm the destroy plan using the same profile, region, bucket name,
and state. `force_destroy = false` prevents Terraform from deleting a bucket
that contains objects. If artifacts have been uploaded later, intentionally
empty the bucket first, including object versions/delete markers if versioning
was enabled outside this skeleton. Do not discard state before cleanup, and do
not change the bucket name or region casually because that can replace resources.

No real AWS plan, apply, or destroy is required for Story 11.1 verification.