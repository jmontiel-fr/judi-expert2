# ==============================================
# Variables — Module CloudFront
# ==============================================

variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "environment" {
  description = "Environnement de déploiement"
  type        = string
}

variable "alb_dns_name" {
  description = "Nom DNS de l'ALB (origin dynamique)"
  type        = string
}

variable "s3_bucket_name" {
  description = "Nom du bucket S3 (pour la bucket policy)"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN du bucket S3 (pour la bucket policy)"
  type        = string
}

variable "s3_bucket_domain_name" {
  description = "Nom de domaine régional du bucket S3 (origin statique)"
  type        = string
}
