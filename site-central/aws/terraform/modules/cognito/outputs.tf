output "user_pool_id" {
  description = "ID du User Pool Cognito"
  value       = aws_cognito_user_pool.main.id
}

output "user_pool_arn" {
  description = "ARN du User Pool Cognito"
  value       = aws_cognito_user_pool.main.arn
}

output "user_pool_client_id" {
  description = "ID du client frontend Cognito"
  value       = aws_cognito_user_pool_client.frontend.id
}

output "user_pool_endpoint" {
  description = "Endpoint du User Pool Cognito"
  value       = aws_cognito_user_pool.main.endpoint
}
