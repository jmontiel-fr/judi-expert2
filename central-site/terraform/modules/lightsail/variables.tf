variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "instance_plan" {
  description = "Lightsail plan ID (nano_3_0=512MB, micro_3_0=1GB, small_3_0=2GB, medium_3_0=4GB)"
  type        = string
  default     = "small_3_0"
}

variable "rds_endpoint" {
  description = "RDS endpoint for database connection"
  type        = string
}

variable "rds_db_name" {
  type = string
}

variable "rds_username" {
  type      = string
  sensitive = true
}

variable "rds_password" {
  type      = string
  sensitive = true
}
