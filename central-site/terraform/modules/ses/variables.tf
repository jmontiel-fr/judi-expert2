variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
}

variable "domain_name" {
  description = "Domaine pour l'envoi d'emails (ex: judi-expert.fr)"
  type        = string
}

variable "route53_zone_id" {
  description = "ID de la zone Route 53 pour le domaine"
  type        = string
}
