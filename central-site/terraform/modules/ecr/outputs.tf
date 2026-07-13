output "backend_repository_url" {
  description = "URL du repo ECR backend"
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_repository_url" {
  description = "URL du repo ECR frontend"
  value       = aws_ecr_repository.frontend.repository_url
}

output "registry_id" {
  description = "AWS Account ID (ECR registry)"
  value       = aws_ecr_repository.backend.registry_id
}
