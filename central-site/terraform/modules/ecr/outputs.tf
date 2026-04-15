output "web_backend_repository_url" {
  description = "URL du dépôt ECR pour judi-web-backend"
  value       = aws_ecr_repository.repos["judi-web-backend"].repository_url
}

output "web_frontend_repository_url" {
  description = "URL du dépôt ECR pour judi-web-frontend"
  value       = aws_ecr_repository.repos["judi-web-frontend"].repository_url
}

output "rag_repository_url" {
  description = "URL du dépôt ECR pour judi-rag"
  value       = aws_ecr_repository.repos["judi-rag"].repository_url
}

output "repository_urls" {
  description = "Map de tous les URLs de dépôts ECR"
  value       = { for k, v in aws_ecr_repository.repos : k => v.repository_url }
}
