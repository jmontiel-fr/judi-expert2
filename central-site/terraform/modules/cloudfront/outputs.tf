# ==============================================
# Outputs — Module CloudFront
# ==============================================

output "distribution_id" {
  description = "ID de la distribution CloudFront"
  value       = aws_cloudfront_distribution.main.id
}

output "domain_name" {
  description = "Nom de domaine de la distribution CloudFront"
  value       = aws_cloudfront_distribution.main.domain_name
}
