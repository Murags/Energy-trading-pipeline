output "bucket_name" {
  description = "Name of the optional S3 artifact bucket."
  value       = aws_s3_bucket.artifacts.bucket
}

output "bucket_arn" {
  description = "ARN of the optional S3 artifact bucket."
  value       = aws_s3_bucket.artifacts.arn
}

output "bucket_uri" {
  description = "S3 URI to which repository-relative artifact paths can be appended."
  value       = "s3://${aws_s3_bucket.artifacts.bucket}"
}

output "aws_region" {
  description = "Configured region of the optional S3 artifact bucket."
  value       = var.aws_region
}

output "artifact_prefixes" {
  description = "Local artifact directories mapped to matching S3 key prefixes."
  value = tomap({
    "data/raw"                  = "data/raw/"
    "data/processed"            = "data/processed/"
    "data/features"             = "data/features/"
    "models"                    = "models/"
    "logs"                      = "logs/"
    "reports/tables"            = "reports/tables/"
    "reports/figures"           = "reports/figures/"
    "reports/dashboard_exports" = "reports/dashboard_exports/"
  })
}

output "forecast_repository_url" {
  description = "ECR repository URL for the Lambda image."
  value       = aws_ecr_repository.forecast.repository_url
}

output "dashboard_repository_url" {
  description = "ECR repository URL for the dashboard image."
  value       = aws_ecr_repository.dashboard.repository_url
}

output "lambda_function_name" {
  description = "Name of the scheduled forecast Lambda."
  value       = try(aws_lambda_function.forecast[0].function_name, null)
}

output "schedule_arn" {
  description = "ARN of the 18:15 Europe/Berlin daily schedule."
  value       = try(aws_scheduler_schedule.daily_forecast[0].arn, null)
}

output "dashboard_cluster_name" {
  description = "ECS cluster used for manually started dashboard tasks."
  value       = aws_ecs_cluster.dashboard.name
}

output "dashboard_task_definition_arn" {
  description = "Task definition to run only while the dashboard is needed."
  value       = try(aws_ecs_task_definition.dashboard[0].arn, null)
}

output "dashboard_subnet_id" {
  description = "Public subnet supplied to the on-demand ECS run-task command."
  value       = aws_subnet.dashboard.id
}

output "dashboard_security_group_id" {
  description = "Security group supplied to the on-demand ECS run-task command."
  value       = aws_security_group.dashboard.id
}
