# Keyless image publishing from GitHub Actions.
#
# GitHub's OIDC token is exchanged for short-lived credentials of a role that
# only the configured repository's default branch can assume, and that can only
# push to the two ECR repositories. No AWS keys are stored in GitHub. Rolling a
# new image out to Lambda or ECS stays a reviewed, local `terraform apply`.

locals {
  github_oidc_enabled = var.github_repository != null
  github_oidc_host    = "token.actions.githubusercontent.com"
}

resource "aws_iam_openid_connect_provider" "github" {
  count = local.github_oidc_enabled ? 1 : 0

  url            = "https://${local.github_oidc_host}"
  client_id_list = ["sts.amazonaws.com"]
  tags           = var.tags
}

resource "aws_iam_role" "github_image_publisher" {
  count = local.github_oidc_enabled ? 1 : 0

  name                 = "${var.name_prefix}-github-image-publisher"
  max_session_duration = 3600
  tags                 = var.tags
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.github[0].arn }
      Condition = {
        StringEquals = {
          "${local.github_oidc_host}:aud" = "sts.amazonaws.com"
          "${local.github_oidc_host}:sub" = "repo:${var.github_repository}:ref:refs/heads/${var.github_deploy_branch}"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_image_publisher" {
  count = local.github_oidc_enabled ? 1 : 0

  name = "push-pipeline-images"
  role = aws_iam_role.github_image_publisher[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "RegistryLogin"
        Effect   = "Allow"
        Action   = "ecr:GetAuthorizationToken"
        Resource = "*"
      },
      {
        Sid    = "PushPipelineImages"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeImages",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = [
          aws_ecr_repository.forecast.arn,
          aws_ecr_repository.dashboard.arn,
        ]
      },
    ]
  })
}
