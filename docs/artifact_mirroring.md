# Optional Artifact Mirroring

`energy_trading_pipeline.utils.aws.mirror_artifacts` copies explicitly selected
report, log, or model files to an existing S3 bucket. Local artifacts remain the
source of truth. Run the utility separately after producing local outputs; local
CLI stages and the dashboard do not invoke it, even with enabled AWS settings.

## Configuration

`configs/experiment.yaml` includes disabled defaults. Copy it to a local experiment
configuration and set its optional `aws` section when mirroring is wanted:

```yaml
aws:
  enabled: true
  bucket_name: your-existing-artifact-bucket
  region: eu-central-1
  prefixes:
    models: models/
    logs: logs/
    reports: reports/
```

`prefixes` maps local directory roots to S3 key prefixes. Relative local roots and
selected file paths resolve against the explicit `base_dir` argument. Absolute
local roots are supported for artifacts stored outside the repository:

```yaml
  prefixes:
    /mnt/research/models: models/
    /mnt/research/logs: logs/
    /mnt/research/reports: reports/
```

The suffix beneath the mapped local root is preserved. For example,
`models/artifacts/model_20261010_120000/model.json` becomes
`s3://<bucket>/models/artifacts/model_20261010_120000/model.json` with the default
mapping. Run IDs, model versions, and nested report paths are retained. A custom
prefix such as `demo/reports/` adds that configured namespace before the suffix.
See [the Terraform layout](../infrastructure/terraform/README.md) for the canonical
artifact prefixes and optional bucket provisioning.

Files must exist and match exactly one mapping. Missing files, directories,
ambiguous mappings, duplicate destination keys, and invalid configuration fail
before contacting AWS. Resolved symlink targets must also lie inside a configured
root. Selection is file-by-file; there is no automatic recursive upload.

## Explicit Invocation

Install the existing optional SDK extra only when needed. Include any other
extras you want to retain in your environment:

```bash
uv sync --locked --extra test --extra aws
```

Use boto3's standard credential chain (environment variables, an authenticated
AWS profile, or a role). No access keys are stored in YAML or accepted by the
utility. The selected identity needs object upload permission (`s3:PutObject`)
scoped to the configured bucket and prefixes; managed multipart transfers may
also need `s3:AbortMultipartUpload`. The utility neither creates buckets nor
checks them via a separate API call.

From the repository root, with your local config copy and existing outputs:

```bash
uv run python -c 'from pathlib import Path; from energy_trading_pipeline.config.loader import load_config; from energy_trading_pipeline.utils.aws import mirror_artifacts; config = load_config(Path("configs/mirror_local.yaml")); print(mirror_artifacts(["reports/dashboard_exports/metrics.parquet"], config.get("aws"), base_dir=Path.cwd()))'
```

Or call the same function from Python, passing any selected report/log/model files:

```python
from pathlib import Path

from energy_trading_pipeline.config.loader import load_config
from energy_trading_pipeline.utils.aws import mirror_artifacts

config = load_config(Path("configs/mirror_local.yaml"))
result = mirror_artifacts(
    [
        "reports/dashboard_exports/metrics.parquet",
        "logs/runs/run_20261010_120000/run_metadata.yaml",
        "models/artifacts/model_20261010_120000/model.json",
    ],
    config.get("aws"),
    base_dir=Path.cwd(),
)
print(result)
```

Run/model identifiers are examples; select files from your actual saved run.
Absent configuration, disabled settings, no selected files, an absent SDK, or
missing/incomplete credentials produce a clear logged skip reason. AWS client
initialization failures are also reported as skips. An upload failure is logged
and recorded while other selected files continue. The returned `MirrorResult`
contains `uploaded_keys`, `failed_keys`, and `skipped_reason`; if credentials are
lost mid-copy, completed uploads and earlier failures remain recorded. A retry
uploads selected files again to the same keys; existing S3 objects may be
overwritten. No local file is changed or deleted, and no remote object is deleted.

## Credential-Free Verification

The mirror tests replace the SDK and S3 client with mocks, including credential
lookup and transfer failures. They require neither the AWS extra nor credentials:

```bash
uv run pytest -q tests/unit/test_aws.py -m aws
uv run pytest -q
```

The existing default marker selection excludes AWS tests from ordinary fixture
runs. The offline suite additionally checks that local CLI execution succeeds
with enabled AWS configuration while the SDK is unavailable.
