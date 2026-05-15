# ==============================================
# Judi-Expert — Module Cron Abonnement (Variables)
# ==============================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, production)"
  type        = string
}

variable "aws_region" {
  description = "Région AWS"
  type        = string
}

variable "api_base_url" {
  description = "URL de base de l'API backend (ex: https://origin.judi-expert.fr:8000)"
  type        = string
}

variable "schedule_expression" {
  description = "Expression cron EventBridge (par défaut : tous les jours à 08:00 UTC)"
  type        = string
  default     = "cron(0 8 * * ? *)"
}

variable "lambda_timeout" {
  description = "Timeout de la Lambda en secondes"
  type        = number
  default     = 60
}
