mock_provider "aws" {
  mock_resource "aws_s3_bucket" {
    defaults = {
      arn = "arn:aws:s3:::energy-pipeline-test-artifacts"
    }
  }
}

variables {
  bucket_name = "energy-pipeline-test-artifacts"
  aws_region  = "eu-central-1"
  tags = {
    project = "energy_trading_pipeline"
  }
}

run "private_encrypted_bucket" {
  command = apply

  assert {
    condition = (
      aws_s3_bucket.artifacts.bucket == var.bucket_name &&
      aws_s3_bucket.artifacts.force_destroy == false &&
      aws_s3_bucket.artifacts.tags == var.tags
    )
    error_message = "The bucket must use explicit configuration and preserve nonempty buckets."
  }

  assert {
    condition = (
      aws_s3_bucket_public_access_block.artifacts.block_public_acls &&
      aws_s3_bucket_public_access_block.artifacts.block_public_policy &&
      aws_s3_bucket_public_access_block.artifacts.ignore_public_acls &&
      aws_s3_bucket_public_access_block.artifacts.restrict_public_buckets
    )
    error_message = "All four public-access protections must be enabled."
  }

  assert {
    condition = (
      aws_s3_bucket_public_access_block.artifacts.bucket == aws_s3_bucket.artifacts.id &&
      aws_s3_bucket_server_side_encryption_configuration.artifacts.bucket == aws_s3_bucket.artifacts.id &&
      aws_s3_bucket_ownership_controls.artifacts.bucket == aws_s3_bucket.artifacts.id
    )
    error_message = "Security controls must target the artifact bucket."
  }

  assert {
    condition = (
      one(one(aws_s3_bucket_server_side_encryption_configuration.artifacts.rule).apply_server_side_encryption_by_default).sse_algorithm == "AES256" &&
      one(aws_s3_bucket_ownership_controls.artifacts.rule).object_ownership == "BucketOwnerEnforced"
    )
    error_message = "Use S3-managed encryption and disable ACLs without adding IAM or KMS resources."
  }

  assert {
    condition = (
      output.bucket_name == var.bucket_name &&
      output.bucket_arn == "arn:aws:s3:::energy-pipeline-test-artifacts" &&
      output.bucket_uri == "s3://${var.bucket_name}" &&
      output.aws_region == var.aws_region
    )
    error_message = "Outputs must identify the configured bucket and region."
  }

  assert {
    condition = output.artifact_prefixes == tomap({
      "data/raw"                  = "data/raw/"
      "data/processed"            = "data/processed/"
      "data/features"             = "data/features/"
      "models"                    = "models/"
      "logs"                      = "logs/"
      "reports/tables"            = "reports/tables/"
      "reports/figures"           = "reports/figures/"
      "reports/dashboard_exports" = "reports/dashboard_exports/"
    })
    error_message = "S3 prefixes must mirror repository-relative artifact paths."
  }
}

run "reject_short_bucket_name" {
  command = plan
  variables {
    bucket_name = "ab"
  }
  expect_failures = [var.bucket_name]
}

run "reject_long_bucket_name" {
  command = plan
  variables {
    bucket_name = "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyzabcdefghijkl"
  }
  expect_failures = [var.bucket_name]
}

run "reject_uppercase_bucket_name" {
  command = plan
  variables {
    bucket_name = "Energy-pipeline-artifacts"
  }
  expect_failures = [var.bucket_name]
}

run "reject_underscore_bucket_name" {
  command = plan
  variables {
    bucket_name = "energy_pipeline_artifacts"
  }
  expect_failures = [var.bucket_name]
}

run "reject_ip_address_bucket_name" {
  command = plan
  variables {
    bucket_name = "192.168.1.1"
  }
  expect_failures = [var.bucket_name]
}

run "reject_trailing_hyphen_bucket_name" {
  command = plan
  variables {
    bucket_name = "energy-pipeline-artifacts-"
  }
  expect_failures = [var.bucket_name]
}

run "reject_reserved_bucket_name" {
  command = plan
  variables {
    bucket_name = "energy-pipeline-s3alias"
  }
  expect_failures = [var.bucket_name]
}

run "documented_optional_usage_and_layout" {
  command = plan

  assert {
    condition = alltrue([
      for local_path, s3_prefix in output.artifact_prefixes :
      strcontains(
        try(file("${path.module}/README.md"), ""),
        "| `${local_path}/` | `${s3_prefix}` |"
      )
    ])
    error_message = "The README must document every local-to-S3 prefix mapping."
  }

  assert {
    condition = alltrue([
      for required_text in [
        "No AWS resources or credentials are required for local pipeline runs",
        "terraform -chdir=infrastructure/terraform init -backend=false -input=false",
        "terraform -chdir=infrastructure/terraform fmt -check",
        "terraform -chdir=infrastructure/terraform validate",
        "terraform -chdir=\"$test_root\" test",
        "terraform -chdir=infrastructure/terraform plan -out=optional_s3.tfplan",
        "terraform -chdir=infrastructure/terraform apply optional_s3.tfplan",
        "terraform -chdir=infrastructure/terraform output",
        "terraform -chdir=infrastructure/terraform destroy",
        "s3:CreateBucket",
        "s3:DeleteBucket",
        "force_destroy = false",
        "forecasts.parquet",
        "metrics.parquet",
        "retraining_events.parquet",
        "model_versions.parquet"
      ] : strcontains(try(file("${path.module}/README.md"), ""), required_text)
    ])
    error_message = "Document credential-free checks, opt-in provisioning, permissions, cleanup, and dashboard exports."
  }
}