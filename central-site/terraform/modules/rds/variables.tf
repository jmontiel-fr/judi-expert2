variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
}

variable "vpc_id" {
  description = "VPC ID where RDS security group will be created"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for the DB subnet group (must be in the same VPC)"
  type        = list(string)
}
