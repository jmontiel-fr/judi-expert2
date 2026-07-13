variable "project_name" {
  description = "Project name"
  type        = string
  default     = "judi-expert"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-3"
}

# --- Lightsail ---

variable "lightsail_plan" {
  description = "Lightsail instance plan (nano_3_0, micro_3_0, small_3_0, medium_3_0)"
  type        = string
  default     = "small_3_0"
}

# --- RDS ---

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "judi_expert"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "judi_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# --- DNS ---

variable "domain_name" {
  description = "Root domain name (e.g. judi-expert.fr)"
  type        = string
  default     = "judi-expert.fr"
}

# Google Search Console — enregistrement TXT fourni par Google (laisser vide si non utilise)
variable "google_site_verification" {
  description = "Valeur TXT Google Search Console (ex: google-site-verification=ABC123...)"
  type        = string
  default     = ""
  sensitive   = false
}

# --- Cognito Users ---

variable "admin_email" {
  description = "Email du compte administrateur Cognito"
  type        = string
  default     = "admin@itechsource.fr"
}

variable "admin_temporary_password" {
  description = "Mot de passe temporaire admin (changement forcé à la 1re connexion)"
  type        = string
  sensitive   = true
}

variable "expert_email" {
  description = "Email du compte expert initial"
  type        = string
  default     = "jacky.montiel@gmail.com"
}

variable "expert_temporary_password" {
  description = "Mot de passe temporaire expert (changement forcé à la 1re connexion)"
  type        = string
  sensitive   = true
}
