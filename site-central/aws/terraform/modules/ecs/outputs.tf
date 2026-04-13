# ==============================================
# Outputs — Module ECS
# ==============================================

output "cluster_id" {
  description = "ID du cluster ECS"
  value       = aws_ecs_cluster.main.id
}

output "cluster_name" {
  description = "Nom du cluster ECS"
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "Nom du service ECS"
  value       = aws_ecs_service.app.name
}

output "task_execution_role_arn" {
  description = "ARN du rôle d'exécution des tâches ECS"
  value       = aws_iam_role.ecs_task_execution.arn
}
