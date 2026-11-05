resource "aws_ecr_repository" "forecast" {
  name                 = "${var.name_prefix}-forecast"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

resource "aws_ecr_repository" "dashboard" {
  name                 = "${var.name_prefix}-dashboard"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = false

  encryption_configuration {
    encryption_type = "AES256"
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "forecast" {
  repository = aws_ecr_repository.forecast.name
  policy     = local.ecr_lifecycle_policy
}

resource "aws_ecr_lifecycle_policy" "dashboard" {
  repository = aws_ecr_repository.dashboard.name
  policy     = local.ecr_lifecycle_policy
}

data "aws_caller_identity" "current" {}

resource "aws_ecr_repository_policy" "forecast_lambda" {
  repository = aws_ecr_repository.forecast.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "LambdaImagePull"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
      Condition = {
        StringLike = {
          "aws:SourceArn" = "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${var.name_prefix}-forecast"
        }
      }
    }]
  })
}

data "aws_ecr_image" "forecast" {
  count = var.deploy_workloads ? 1 : 0

  repository_name = aws_ecr_repository.forecast.name
  image_tag       = var.lambda_image_tag
}

data "aws_ecr_image" "dashboard" {
  count = var.deploy_workloads ? 1 : 0

  repository_name = aws_ecr_repository.dashboard.name
  image_tag       = var.dashboard_image_tag
}

locals {
  ecr_lifecycle_policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Delete untagged build remnants after seven days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 7
      }
      action = { type = "expire" }
    }]
  })
}
