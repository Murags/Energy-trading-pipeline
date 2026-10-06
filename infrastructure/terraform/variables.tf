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
  description = "Tags for the optional artifact bucket."
  type        = map(string)
  default = {
    project = "energy_trading_pipeline"
  }
  nullable = false
}