# ==============================================
# Variables — Module Scheduler (Heures Ouvrables)
# ==============================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Nom du cluster ECS Fargate"
  type        = string
}

variable "ecs_service_name" {
  description = "Nom du service ECS Fargate"
  type        = string
}

variable "rds_instance_id" {
  description = "Identifiant de l'instance RDS PostgreSQL"
  type        = string
}
