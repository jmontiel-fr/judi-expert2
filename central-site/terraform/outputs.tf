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
