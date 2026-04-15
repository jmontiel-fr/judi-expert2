variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
}

variable "db_instance_class" {
  description = "Classe d'instance RDS"
  type        = string
}

variable "db_name" {
  description = "Nom de la base de données"
  type        = string
}

variable "db_username" {
  description = "Nom d'utilisateur de la base de données"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Mot de passe de la base de données"
  type        = string
  sensitive   = true
}

variable "private_subnet_ids" {
  description = "IDs des sous-réseaux privés pour le subnet group RDS"
  type        = list(string)
}

variable "rds_security_group_id" {
  description = "ID du security group RDS"
  type        = string
}
