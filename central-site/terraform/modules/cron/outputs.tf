# ==============================================
# Judi-Expert — Module Cron Abonnement (Outputs)
# ==============================================

output "lambda_function_name" {
  description = "Nom de la Lambda cron abonnement"
  value       = aws_lambda_function.cron_abonnement.function_name
}

output "lambda_function_arn" {
  description = "ARN de la Lambda cron abonnement"
  value       = aws_lambda_function.cron_abonnement.arn
}

output "eventbridge_rule_arn" {
  description = "ARN de la règle EventBridge"
  value       = aws_cloudwatch_event_rule.cron_abonnement.arn
}

output "cron_secret_arn" {
  description = "ARN du secret contenant le token cron"
  value       = aws_secretsmanager_secret.cron_token.arn
}

output "cron_secret_name" {
  description = "Nom du secret contenant le token cron"
  value       = aws_secretsmanager_secret.cron_token.name
}
