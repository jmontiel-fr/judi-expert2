variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement (dev, staging, production)"
  type        = string
}

variable "admin_email" {
  description = "Email du compte administrateur"
  type        = string
  default     = "admin@judi-expert.fr"
}

variable "admin_temporary_password" {
  description = "Mot de passe temporaire du compte admin (changement forcé à la 1re connexion)"
  type        = string
  sensitive   = true
  default     = "JudiAdmin2026!"
}
