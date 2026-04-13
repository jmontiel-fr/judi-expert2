# --- VPC ---
output "vpc_id" {
  description = "ID du VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs des sous-réseaux publics"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs des sous-réseaux privés"
  value       = module.vpc.private_subnet_ids
}

output "alb_security_group_id" {
  description = "ID du security group ALB"
  value       = module.vpc.alb_security_group_id
}

output "ecs_security_group_id" {
  description = "ID du security group ECS"
  value       = module.vpc.ecs_security_group_id
}

output "rds_security_group_id" {
  description = "ID du security group RDS"
  value       = module.vpc.rds_security_group_id
}

# --- ECR ---
output "ecr_web_backend_repository_url" {
  description = "URL du dépôt ECR pour judi-web-backend"
  value       = module.ecr.web_backend_repository_url
}

output "ecr_web_frontend_repository_url" {
  description = "URL du dépôt ECR pour judi-web-frontend"
  value       = module.ecr.web_frontend_repository_url
}

output "ecr_rag_repository_url" {
  description = "URL du dépôt ECR pour judi-rag"
  value       = module.ecr.rag_repository_url
}

# --- RDS ---
output "rds_endpoint" {
  description = "Endpoint de l'instance RDS PostgreSQL"
  value       = module.rds.endpoint
}

output "rds_instance_id" {
  description = "ID de l'instance RDS"
  value       = module.rds.instance_id
}

# --- S3 ---
output "s3_bucket_name" {
  description = "Nom du bucket S3 pour les assets statiques"
  value       = module.s3.bucket_name
}

output "s3_bucket_arn" {
  description = "ARN du bucket S3"
  value       = module.s3.bucket_arn
}

output "s3_bucket_domain_name" {
  description = "Nom de domaine du bucket S3"
  value       = module.s3.bucket_domain_name
}

# --- ALB ---
output "alb_arn" {
  description = "ARN de l'Application Load Balancer"
  value       = module.alb.alb_arn
}

output "alb_dns_name" {
  description = "Nom DNS de l'ALB"
  value       = module.alb.alb_dns_name
}

output "backend_target_group_arn" {
  description = "ARN du target group backend"
  value       = module.alb.backend_target_group_arn
}

output "frontend_target_group_arn" {
  description = "ARN du target group frontend"
  value       = module.alb.frontend_target_group_arn
}

output "http_listener_arn" {
  description = "ARN du listener HTTP de l'ALB"
  value       = module.alb.http_listener_arn
}

# --- ECS ---
output "ecs_cluster_id" {
  description = "ID du cluster ECS"
  value       = module.ecs.cluster_id
}

output "ecs_cluster_name" {
  description = "Nom du cluster ECS"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Nom du service ECS"
  value       = module.ecs.service_name
}

output "ecs_task_execution_role_arn" {
  description = "ARN du rôle d'exécution des tâches ECS"
  value       = module.ecs.task_execution_role_arn
}

# --- Cognito ---
output "cognito_user_pool_id" {
  description = "ID du User Pool Cognito"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "ID du client frontend Cognito"
  value       = module.cognito.user_pool_client_id
}

output "cognito_user_pool_endpoint" {
  description = "Endpoint du User Pool Cognito"
  value       = module.cognito.user_pool_endpoint
}

# --- CloudFront ---
output "cloudfront_distribution_id" {
  description = "ID de la distribution CloudFront"
  value       = module.cloudfront.distribution_id
}

output "cloudfront_domain_name" {
  description = "Nom de domaine de la distribution CloudFront"
  value       = module.cloudfront.domain_name
}

# --- Scheduler ---
output "scheduler_start_lambda_arn" {
  description = "ARN de la Lambda de démarrage du site"
  value       = module.scheduler.start_lambda_arn
}

output "scheduler_stop_lambda_arn" {
  description = "ARN de la Lambda d'arrêt du site"
  value       = module.scheduler.stop_lambda_arn
}

output "scheduler_start_schedule_arn" {
  description = "ARN du schedule EventBridge de démarrage"
  value       = module.scheduler.start_schedule_arn
}

output "scheduler_stop_schedule_arn" {
  description = "ARN du schedule EventBridge d'arrêt"
  value       = module.scheduler.stop_schedule_arn
}
