locals {
  lambda_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
  scheduler_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "scheduler.amazonaws.com" }
    }]
  })
  ecs_assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "lambda" {
  name               = "${var.name_prefix}-forecast-lambda"
  assume_role_policy = local.lambda_assume_role_policy
  tags               = var.tags
}

resource "aws_iam_role_policy" "lambda" {
  name = "forecast-runtime"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "WriteFunctionLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      },
      {
        Sid      = "ListArtifactStore"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.artifacts.arn
        Condition = {
          StringLike = { "s3:prefix" = ["live", "live/*", "market", "market/*"] }
        }
      },
      {
        Sid      = "ReadWriteLiveArtifacts"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject"]
        Resource = ["${aws_s3_bucket.artifacts.arn}/live/*", "${aws_s3_bucket.artifacts.arn}/market/*"]
      },
    ]
  })
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.name_prefix}-scheduler"
  assume_role_policy = local.scheduler_assume_role_policy
  tags               = var.tags
}

resource "aws_iam_role_policy" "scheduler" {
  count = var.deploy_workloads ? 1 : 0

  name = "invoke-forecast"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.forecast[0].arn
    }]
  })
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${var.name_prefix}-dashboard-execution"
  assume_role_policy = local.ecs_assume_role_policy
  tags               = var.tags
}

resource "aws_iam_role_policy" "ecs_execution" {
  name = "pull-dashboard-image-and-write-logs"
  role = aws_iam_role.ecs_execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EcrLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid      = "PullDashboardImage"
        Effect   = "Allow"
        Action   = ["ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = aws_ecr_repository.dashboard.arn
      },
      {
        Sid      = "WriteDashboardLogs"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.dashboard.arn}:*"
      },
    ]
  })
}

resource "aws_iam_role" "dashboard" {
  name               = "${var.name_prefix}-dashboard-task"
  assume_role_policy = local.ecs_assume_role_policy
  tags               = var.tags
}

resource "aws_iam_role_policy" "dashboard" {
  name = "read-dashboard-artifacts"
  role = aws_iam_role.dashboard.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListArtifactStore"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.artifacts.arn
        Condition = {
          StringLike = { "s3:prefix" = ["live", "live/*", "reports/dashboard_exports", "reports/dashboard_exports/*"] }
        }
      },
      {
        Sid      = "ReadLiveArtifacts"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = ["${aws_s3_bucket.artifacts.arn}/live/*", "${aws_s3_bucket.artifacts.arn}/reports/dashboard_exports/*"]
      },
    ]
  })
}
