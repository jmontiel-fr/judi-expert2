# ==============================================
# Variables — Module ALB
# ==============================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
}

variable "vpc_id" {
  description = "ID du VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "IDs des sous-réseaux publics pour l'ALB"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "ID du security group ALB"
  type        = string
}
