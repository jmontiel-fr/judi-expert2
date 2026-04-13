variable "project_name" {
  description = "Nom du projet"
  type        = string
  default     = "judi-expert"
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "Région AWS"
  type        = string
  default     = "eu-west-3"
}

variable "vpc_cidr" {
  description = "CIDR block pour le VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Zones de disponibilité"
  type        = list(string)
  default     = ["eu-west-3a", "eu-west-3b"]
}

variable "db_instance_class" {
  description = "Classe d'instance RDS"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Nom de la base de données PostgreSQL"
  type        = string
  default     = "judi_expert"
}

variable "db_username" {
  description = "Nom d'utilisateur de la base de données"
  type        = string
  default     = "judi_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Mot de passe de la base de données"
  type        = string
  sensitive   = true
}

# --- ECS / Container Images ---

variable "backend_image" {
  description = "Image Docker du backend (URI ECR ou placeholder)"
  type        = string
  default     = "nginx:alpine"
}

variable "frontend_image" {
  description = "Image Docker du frontend (URI ECR ou placeholder)"
  type        = string
  default     = "nginx:alpine"
}
