output "bucket_name" {
  description = "Nom du bucket S3"
  value       = aws_s3_bucket.assets.id
}

output "bucket_arn" {
  description = "ARN du bucket S3"
  value       = aws_s3_bucket.assets.arn
}

output "bucket_domain_name" {
  description = "Nom de domaine du bucket S3"
  value       = aws_s3_bucket.assets.bucket_regional_domain_name
}
