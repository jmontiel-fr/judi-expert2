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
