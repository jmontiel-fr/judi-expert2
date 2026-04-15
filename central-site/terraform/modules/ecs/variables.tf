# ==============================================
# Variables — Module ECS
# ==============================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
}

variable "aws_region" {
  description = "Région AWS"
  type        = string
}

variable "private_subnet_ids" {
  description = "IDs des sous-réseaux privés pour les tâches ECS"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "ID du security group ECS"
  type        = string
}

variable "backend_target_group_arn" {
  description = "ARN du target group ALB pour le backend"
  type        = string
}

variable "frontend_target_group_arn" {
  description = "ARN du target group ALB pour le frontend"
  type        = string
}

variable "http_listener_arn" {
  description = "ARN du listener HTTP de l'ALB (pour depends_on)"
  type        = string
}

# --- Task Definition ---

variable "task_cpu" {
  description = "CPU total pour la task definition (en unités CPU)"
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "Mémoire totale pour la task definition (en MiB)"
  type        = string
  default     = "1024"
}

variable "backend_image" {
  description = "Image Docker du backend (URI ECR ou placeholder)"
  type        = string
  default     = "nginx:alpine"
}

variable "backend_cpu" {
  description = "CPU alloué au conteneur backend"
  type        = number
  default     = 256
}

variable "backend_memory" {
  description = "Mémoire allouée au conteneur backend (MiB)"
  type        = number
  default     = 512
}

variable "backend_environment" {
  description = "Variables d'environnement pour le conteneur backend"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "frontend_image" {
  description = "Image Docker du frontend (URI ECR ou placeholder)"
  type        = string
  default     = "nginx:alpine"
}

variable "frontend_cpu" {
  description = "CPU alloué au conteneur frontend"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Mémoire allouée au conteneur frontend (MiB)"
  type        = number
  default     = 512
}

variable "frontend_environment" {
  description = "Variables d'environnement pour le conteneur frontend"
  type = list(object({
    name  = string
    value = string
  }))
  default = []
}

variable "desired_count" {
  description = "Nombre de tâches ECS souhaitées (0 pour scale-to-zero)"
  type        = number
  default     = 1
}
