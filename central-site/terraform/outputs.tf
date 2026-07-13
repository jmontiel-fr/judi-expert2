# --- Lightsail ---
output "lightsail_public_ip" {
  description = "Lightsail instance public IP (SSH access)"
  value       = module.lightsail.public_ip
}

output "lightsail_instance_name" {
  description = "Lightsail instance name"
  value       = module.lightsail.instance_name
}

# --- RDS ---
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = module.rds.endpoint
}

# --- Cognito ---
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.cognito.user_pool_client_id
}

# --- CloudFront ---
output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name"
  value       = module.cloudfront.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.distribution_id
}

# --- DNS ---
output "route53_name_servers" {
  description = "Name servers to configure in Gandi"
  value       = module.dns.name_servers
}

# --- Cron Abonnement ---
output "cron_lambda_function_name" {
  description = "Nom de la Lambda cron abonnement"
  value       = module.cron.lambda_function_name
}

output "cron_lambda_function_arn" {
  description = "ARN de la Lambda cron abonnement"
  value       = module.cron.lambda_function_arn
}

output "cron_secret_name" {
  description = "Nom du secret Secrets Manager contenant le token cron"
  value       = module.cron.cron_secret_name
}

# --- S3 (packages Site Client) ---
output "s3_assets_bucket_name" {
  description = "Nom du bucket S3 pour les packages Site Client"
  value       = module.s3.bucket_name
}

output "s3_backend_access_key_id" {
  description = "Access Key ID pour le backend (presigned URLs S3)"
  value       = module.s3.backend_s3_access_key_id
  sensitive   = true
}

output "s3_backend_secret_access_key" {
  description = "Secret Access Key pour le backend (presigned URLs S3)"
  value       = module.s3.backend_s3_secret_access_key
  sensitive   = true
}

# --- ECR (Docker Registry, eu-west-1) ---
output "ecr_backend_repository_url" {
  description = "ECR backend repository URL"
  value       = module.ecr.backend_repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR frontend repository URL"
  value       = module.ecr.frontend_repository_url
}
