variable "bucket_name" {
  description = "Globally unique artifact bucket name; use lowercase alphanumeric words separated by single hyphens."
  type        = string
  nullable    = false

  validation {
    condition = (
      length(var.bucket_name) >= 3 &&
      length(var.bucket_name) <= 63 &&
      can(regex("^[a-z0-9]+(-[a-z0-9]+)*$", var.bucket_name)) &&
      !startswith(var.bucket_name, "sthree-") &&
      !startswith(var.bucket_name, "amzn-s3-demo-") &&
      !endswith(var.bucket_name, "-s3alias") &&
      !endswith(var.bucket_name, "-ext-s3") &&
      !endswith(var.bucket_name, "-table-s3")
    )
    error_message = "Use 3-63 lowercase letters/digits separated by single hyphens, without AWS-reserved prefixes or suffixes."
  }
}

variable "aws_region" {
  description = "AWS region for the optional artifact bucket."
  type        = string
  default     = "eu-central-1"
  nullable    = false
}

variable "tags" {
  description = "Tags applied to supported resources in the optional AWS stack."
  type        = map(string)
  default = {
    project = "energy_trading_pipeline"
  }
  nullable = false
}

variable "name_prefix" {
  description = "Lowercase prefix used for AWS resource names."
  type        = string
  default     = "energy-trading-pipeline"
  nullable    = false

  validation {
    condition     = can(regex("^[a-z0-9]+(-[a-z0-9]+)*$", var.name_prefix)) && length(var.name_prefix) <= 40
    error_message = "Use at most 40 lowercase letters/digits separated by single hyphens."
  }
}

variable "lambda_image_tag" {
  description = "Immutable tag pushed to the forecast ECR repository before Lambda is created or updated."
  type        = string
  default     = "latest"
  nullable    = false
}

variable "dashboard_image_tag" {
  description = "Immutable tag pushed to the dashboard ECR repository before its Fargate task is run."
  type        = string
  default     = "latest"
  nullable    = false
}

variable "deploy_workloads" {
  description = "Create Lambda, its schedule, and the dashboard task definition after both images have been pushed to ECR."
  type        = bool
  default     = false
}

variable "lambda_memory_mb" {
  description = "Memory allocated to the daily forecast Lambda; the default fits accounts limited to 3008 MiB."
  type        = number
  default     = 3008

  validation {
    condition     = var.lambda_memory_mb >= 1024 && var.lambda_memory_mb <= 10240
    error_message = "lambda_memory_mb must be between 1024 and 10240."
  }
}

variable "lambda_timeout_seconds" {
  description = "Maximum duration of one forecast invocation."
  type        = number
  default     = 900

  validation {
    condition     = var.lambda_timeout_seconds >= 1 && var.lambda_timeout_seconds <= 900
    error_message = "lambda_timeout_seconds must be between 1 and 900."
  }
}

variable "schedule_enabled" {
  description = "Whether EventBridge Scheduler invokes the forecast each day."
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "CloudWatch log retention for Lambda and the dashboard task."
  type        = number
  default     = 14

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.log_retention_days)
    error_message = "Use a CloudWatch-supported retention period up to 365 days."
  }
}

variable "dashboard_allowed_cidr" {
  description = "Single trusted IPv4 CIDR allowed to reach the on-demand dashboard, normally your public IP with /32."
  type        = string
  nullable    = false

  validation {
    condition     = can(cidrnetmask(var.dashboard_allowed_cidr)) && can(regex("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}/32$", var.dashboard_allowed_cidr))
    error_message = "Provide one valid IPv4 address with a /32 prefix."
  }
}

variable "dashboard_cpu" {
  description = "Fargate CPU units for an on-demand dashboard task."
  type        = number
  default     = 1024
}

variable "dashboard_memory_mb" {
  description = "Fargate memory in MiB for an on-demand dashboard task."
  type        = number
  default     = 4096
}

variable "vpc_cidr" {
  description = "CIDR for the small dashboard VPC."
  type        = string
  default     = "10.42.0.0/24"

  validation {
    condition     = can(cidrsubnet(var.vpc_cidr, 1, 0)) && can(regex("^(?:[0-9]{1,3}\\.){3}[0-9]{1,3}/(?:1[6-9]|2[0-4])$", var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 /16 through /24 network."
  }
}

variable "noncurrent_version_retention_days" {
  description = "Days to retain replaced S3 object versions before automatic expiration."
  type        = number
  default     = 30

  validation {
    condition     = var.noncurrent_version_retention_days >= 7
    error_message = "Retain noncurrent object versions for at least seven days."
  }
}

variable "budget_limit_usd" {
  description = "Monthly account-level AWS cost budget in USD."
  type        = number
  default     = 10

  validation {
    condition     = var.budget_limit_usd > 0
    error_message = "budget_limit_usd must be greater than zero."
  }
}

variable "budget_notification_email" {
  description = "Email address that receives 80% forecast and 100% actual budget notifications."
  type        = string
  nullable    = false

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^@[:space:]]+\\.[^@[:space:]]+$", var.budget_notification_email))
    error_message = "Provide a valid budget notification email address."
  }
}
