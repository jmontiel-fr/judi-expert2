output "vpc_id" {
  description = "Default VPC ID (peered with Lightsail)"
  value       = data.aws_vpc.default.id
}

output "subnet_ids" {
  description = "Default VPC subnet IDs (for RDS subnet group)"
  value       = data.aws_subnets.default.ids
}
