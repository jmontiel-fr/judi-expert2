output "bucket_name" {
  description = "Nom du bucket S3 pour les packages"
  value       = aws_s3_bucket.assets.bucket
}

output "bucket_arn" {
  description = "ARN du bucket S3"
  value       = aws_s3_bucket.assets.arn
}

output "bucket_regional_domain_name" {
  description = "Domaine régional du bucket"
  value       = aws_s3_bucket.assets.bucket_regional_domain_name
}

output "backend_s3_access_key_id" {
  description = "Access Key ID pour le backend (presigned URLs)"
  value       = aws_iam_access_key.backend_s3.id
  sensitive   = true
}

output "backend_s3_secret_access_key" {
  description = "Secret Access Key pour le backend (presigned URLs)"
  value       = aws_iam_access_key.backend_s3.secret
  sensitive   = true
}
