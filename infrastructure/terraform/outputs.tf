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