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
  default     = "admin@itechsource.fr"
}

variable "admin_temporary_password" {
  description = "Mot de passe temporaire du compte admin (changement forcé à la 1re connexion)"
  type        = string
  sensitive   = true
}

variable "expert_email" {
  description = "Email du compte expert initial"
  type        = string
  default     = "jacky.montiel@gmail.com"
}

variable "expert_temporary_password" {
  description = "Mot de passe temporaire du compte expert (changement forcé à la 1re connexion)"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Domaine pour l'envoi d'emails (ex: judi-expert.fr)"
  type        = string
}

variable "ses_domain_identity_arn" {
  description = "ARN de l'identité SES du domaine pour l'envoi d'emails"
  type        = string
}
