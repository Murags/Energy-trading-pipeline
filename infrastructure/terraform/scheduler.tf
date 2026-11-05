resource "aws_scheduler_schedule" "daily_forecast" {
  count = var.deploy_workloads ? 1 : 0

  name                         = "${var.name_prefix}-daily-forecast"
  description                  = "Run the next-day forecast at 18:15 Europe/Berlin."
  state                        = var.schedule_enabled ? "ENABLED" : "DISABLED"
  schedule_expression          = "cron(15 18 * * ? *)"
  schedule_expression_timezone = "Europe/Berlin"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.forecast[0].arn
    role_arn = aws_iam_role.scheduler.arn

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  depends_on = [aws_iam_role_policy.scheduler]
}
