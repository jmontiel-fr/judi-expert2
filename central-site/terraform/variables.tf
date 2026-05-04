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
  default     = "eu-west-1"
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
