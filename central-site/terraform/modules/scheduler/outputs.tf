# ==============================================
# Outputs — Module Scheduler (Heures Ouvrables)
# ==============================================

output "start_lambda_arn" {
  description = "ARN de la Lambda de démarrage du site"
  value       = aws_lambda_function.site_start.arn
}

output "stop_lambda_arn" {
  description = "ARN de la Lambda d'arrêt du site"
  value       = aws_lambda_function.site_stop.arn
}

output "start_schedule_arn" {
  description = "ARN du schedule EventBridge de démarrage"
  value       = aws_scheduler_schedule.site_start.arn
}

output "stop_schedule_arn" {
  description = "ARN du schedule EventBridge d'arrêt"
  value       = aws_scheduler_schedule.site_stop.arn
}
