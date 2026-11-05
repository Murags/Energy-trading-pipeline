resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.name_prefix}-forecast"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function" "forecast" {
  count = var.deploy_workloads ? 1 : 0

  function_name = "${var.name_prefix}-forecast"
  description   = "Issue the German-French day-ahead spread forecast."
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.forecast.repository_url}@${data.aws_ecr_image.forecast[0].image_digest}"
  role          = aws_iam_role.lambda.arn
  architectures = ["x86_64"]
  memory_size   = var.lambda_memory_mb
  timeout       = var.lambda_timeout_seconds

  ephemeral_storage {
    size = 4096
  }

  environment {
    variables = {
      ETP_CONFIG       = "configs/experiment_day_ahead_pvwind.yaml"
      ETP_LOG_LEVEL    = "INFO"
      ETP_MODEL_PARAMS = "configs/model_params.yaml"
      ETP_STORE        = "s3://${aws_s3_bucket.artifacts.bucket}"
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_ecr_repository_policy.forecast_lambda,
    aws_iam_role_policy.lambda,
  ]

  lifecycle {
    precondition {
      condition     = var.lambda_image_tag != "latest"
      error_message = "Use an immutable lambda_image_tag instead of latest when deploy_workloads is true."
    }
  }

  tags = var.tags
}
