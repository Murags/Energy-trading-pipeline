resource "aws_ecs_cluster" "dashboard" {
  name = "${var.name_prefix}-dashboard"
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/ecs/${var.name_prefix}-dashboard"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_ecs_task_definition" "dashboard" {
  count = var.deploy_workloads ? 1 : 0

  family                   = "${var.name_prefix}-dashboard"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.dashboard_cpu)
  memory                   = tostring(var.dashboard_memory_mb)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.dashboard.arn

  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([{
    name      = "dashboard"
    image     = "${aws_ecr_repository.dashboard.repository_url}@${data.aws_ecr_image.dashboard[0].image_digest}"
    essential = true
    command = [
      "python", "-m", "streamlit", "run",
      "src/energy_trading_pipeline/dashboard/app.py",
      "--server.address=0.0.0.0",
      "--server.port=8501",
      "--server.headless=true",
      "--browser.gatherUsageStats=false",
    ]
    portMappings = [{
      containerPort = 8501
      hostPort      = 8501
      protocol      = "tcp"
    }]
    environment = [
      { name = "ARROW_DEFAULT_MEMORY_POOL", value = "system" },
      { name = "AWS_REGION", value = var.aws_region },
      { name = "ETP_STORE", value = "s3://${aws_s3_bucket.artifacts.bucket}" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.dashboard.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "dashboard"
      }
    }
  }])

  depends_on = [
    aws_cloudwatch_log_group.dashboard,
    aws_iam_role_policy.ecs_execution,
  ]

  lifecycle {
    precondition {
      condition = contains(lookup({
        256   = [512, 1024, 2048]
        512   = [1024, 2048, 3072, 4096]
        1024  = [2048, 3072, 4096, 5120, 6144, 7168, 8192]
        2048  = range(4096, 17408, 1024)
        4096  = range(8192, 31744, 1024)
        8192  = range(16384, 61441, 4096)
        16384 = range(32768, 122881, 8192)
      }, tostring(var.dashboard_cpu), []), var.dashboard_memory_mb)
      error_message = "dashboard_cpu and dashboard_memory_mb must be a supported Fargate combination."
    }

    precondition {
      condition     = var.dashboard_image_tag != "latest"
      error_message = "Use an immutable dashboard_image_tag instead of latest when deploy_workloads is true."
    }
  }

  tags = var.tags
}
