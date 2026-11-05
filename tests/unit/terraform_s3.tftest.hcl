mock_provider "aws" {
  mock_resource "aws_s3_bucket" {
    defaults = {
      arn = "arn:aws:s3:::energy-pipeline-test-artifacts"
    }
  }

  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/mock-role"
    }
  }

  mock_resource "aws_ecr_repository" {
    defaults = {
      arn            = "arn:aws:ecr:eu-central-1:123456789012:repository/mock"
      repository_url = "123456789012.dkr.ecr.eu-central-1.amazonaws.com/mock"
    }
  }

  mock_resource "aws_lambda_function" {
    defaults = {
      arn = "arn:aws:lambda:eu-central-1:123456789012:function:mock"
    }
  }

  mock_data "aws_caller_identity" {
    defaults = {
      account_id = "123456789012"
    }
  }

  mock_data "aws_ecr_image" {
    defaults = {
      image_digest = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    }
  }
}

variables {
  bucket_name               = "energy-pipeline-test-artifacts"
  aws_region                = "eu-central-1"
  budget_notification_email = "researcher@example.com"
  dashboard_allowed_cidr    = "203.0.113.7/32"
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
      aws_s3_bucket_ownership_controls.artifacts.bucket == aws_s3_bucket.artifacts.id &&
      aws_s3_bucket_versioning.artifacts.bucket == aws_s3_bucket.artifacts.id &&
      aws_s3_bucket_lifecycle_configuration.artifacts.bucket == aws_s3_bucket.artifacts.id
    )
    error_message = "Security controls must target the artifact bucket."
  }

  assert {
    condition = (
      one(one(aws_s3_bucket_server_side_encryption_configuration.artifacts.rule).apply_server_side_encryption_by_default).sse_algorithm == "AES256" &&
      one(aws_s3_bucket_ownership_controls.artifacts.rule).object_ownership == "BucketOwnerEnforced" &&
      one(aws_s3_bucket_versioning.artifacts.versioning_configuration).status == "Enabled" &&
      one(aws_s3_bucket_lifecycle_configuration.artifacts.rule).noncurrent_version_expiration[0].noncurrent_days == 30
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

run "optional_aws_runtime_contract" {
  command = apply

  variables {
    deploy_workloads    = true
    lambda_image_tag    = "release-1"
    dashboard_image_tag = "release-1"
  }

  assert {
    condition = (
      aws_ecr_repository.forecast.image_tag_mutability == "IMMUTABLE" &&
      aws_ecr_repository.dashboard.image_tag_mutability == "IMMUTABLE" &&
      one(aws_ecr_repository.forecast.image_scanning_configuration).scan_on_push &&
      one(aws_ecr_repository.dashboard.image_scanning_configuration).scan_on_push
    )
    error_message = "Both images must use immutable, scan-on-push ECR repositories."
  }

  assert {
    condition = (
      aws_lambda_function.forecast[0].package_type == "Image" &&
      endswith(aws_lambda_function.forecast[0].image_uri, "@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa") &&
      aws_lambda_function.forecast[0].timeout == 900 &&
      aws_lambda_function.forecast[0].environment[0].variables.ETP_STORE == "s3://${var.bucket_name}"
    )
    error_message = "Lambda must run the forecast image with the S3 artifact store."
  }

  assert {
    condition = (
      aws_scheduler_schedule.daily_forecast[0].schedule_expression == "cron(15 18 * * ? *)" &&
      aws_scheduler_schedule.daily_forecast[0].schedule_expression_timezone == "Europe/Berlin" &&
      aws_scheduler_schedule.daily_forecast[0].state == "ENABLED" &&
      one(aws_scheduler_schedule.daily_forecast[0].flexible_time_window).mode == "OFF"
    )
    error_message = "The daily schedule must run exactly at 18:15 Europe/Berlin."
  }

  assert {
    condition = (
      aws_cloudwatch_log_group.lambda.retention_in_days == 14 &&
      aws_cloudwatch_log_group.dashboard.retention_in_days == 14 &&
      contains(aws_ecs_task_definition.dashboard[0].requires_compatibilities, "FARGATE") &&
      contains(one(aws_security_group.dashboard.ingress).cidr_blocks, var.dashboard_allowed_cidr) &&
      contains(
        [
          for item in jsondecode(aws_ecs_task_definition.dashboard[0].container_definitions)[0].environment :
          "${item.name}=${item.value}"
        ],
        "ARROW_DEFAULT_MEMORY_POOL=system"
      )
    )
    error_message = "CloudWatch retention, Arrow stability, and restricted Fargate networking must be explicit."
  }

  assert {
    condition = (
      aws_budgets_budget.monthly.limit_amount == tostring(var.budget_limit_usd) &&
      length(aws_budgets_budget.monthly.notification) == 2
    )
    error_message = "The stack must include forecast and actual monthly budget notifications."
  }


  assert {
    condition = (
      strcontains(aws_iam_role_policy.lambda.policy, "s3:prefix") &&
      strcontains(aws_iam_role_policy.dashboard.policy, "s3:prefix") &&
      strcontains(aws_iam_role_policy.ecs_execution.policy, aws_ecr_repository.dashboard.arn)
    )
    error_message = "Runtime IAM must prefix-scope bucket listings and repository-scope dashboard image pulls."
  }
}

run "reject_public_dashboard_access" {
  command = plan
  variables {
    dashboard_allowed_cidr = "0.0.0.0/0"
  }
  expect_failures = [var.dashboard_allowed_cidr]
}

run "reject_equivalent_public_dashboard_access" {
  command = plan
  variables {
    dashboard_allowed_cidr = "0.0.0.1/0"
  }
  expect_failures = [var.dashboard_allowed_cidr]
}

run "reject_non_immutable_workload_tags" {
  command = plan
  variables {
    deploy_workloads = true
  }
  expect_failures = [
    aws_lambda_function.forecast[0],
    aws_ecs_task_definition.dashboard[0],
  ]
}

run "reject_invalid_budget_email" {
  command = plan
  variables {
    budget_notification_email = "not-an-email"
  }
  expect_failures = [var.budget_notification_email]
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
        "terraform -chdir=infrastructure/terraform plan -out=bootstrap.tfplan",
        "terraform -chdir=infrastructure/terraform apply bootstrap.tfplan",
        "terraform -chdir=infrastructure/terraform plan -out=workloads.tfplan",
        "terraform -chdir=infrastructure/terraform plan -destroy -out=destroy.tfplan",
        "deploy_workloads = false",
        "deploy_workloads    = true",
        "aws ecs run-task",
        "aws ecs stop-task",
        "18:15 `Europe/Berlin`",
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
