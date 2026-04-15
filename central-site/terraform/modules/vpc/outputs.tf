output "vpc_id" {
  description = "ID du VPC"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs des sous-réseaux publics"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs des sous-réseaux privés"
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  description = "ID du security group ALB"
  value       = aws_security_group.alb.id
}

output "ecs_security_group_id" {
  description = "ID du security group ECS"
  value       = aws_security_group.ecs.id
}

output "rds_security_group_id" {
  description = "ID du security group RDS"
  value       = aws_security_group.rds.id
}
