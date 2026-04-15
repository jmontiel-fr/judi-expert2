# ==============================================
# Judi-Expert — Infrastructure AWS (Site Central)
# ==============================================

module "vpc" {
  source = "./modules/vpc"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
}

module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

module "rds" {
  source = "./modules/rds"

  project_name          = var.project_name
  environment           = var.environment
  db_instance_class     = var.db_instance_class
  db_name               = var.db_name
  db_username           = var.db_username
  db_password           = var.db_password
  private_subnet_ids    = module.vpc.private_subnet_ids
  rds_security_group_id = module.vpc.rds_security_group_id
}

module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

module "alb" {
  source = "./modules/alb"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = module.vpc.vpc_id
  public_subnet_ids     = module.vpc.public_subnet_ids
  alb_security_group_id = module.vpc.alb_security_group_id
}

module "ecs" {
  source = "./modules/ecs"

  project_name              = var.project_name
  environment               = var.environment
  aws_region                = var.aws_region
  private_subnet_ids        = module.vpc.private_subnet_ids
  ecs_security_group_id     = module.vpc.ecs_security_group_id
  backend_target_group_arn  = module.alb.backend_target_group_arn
  frontend_target_group_arn = module.alb.frontend_target_group_arn
  http_listener_arn         = module.alb.http_listener_arn
  backend_image             = var.backend_image
  frontend_image            = var.frontend_image
  backend_environment = [
    { name = "DATABASE_URL", value = "postgresql://${var.db_username}:${var.db_password}@${module.rds.endpoint}/${var.db_name}" }
  ]
}

module "cognito" {
  source = "./modules/cognito"

  project_name = var.project_name
  environment  = var.environment
}

module "cloudfront" {
  source = "./modules/cloudfront"

  project_name          = var.project_name
  environment           = var.environment
  alb_dns_name          = module.alb.alb_dns_name
  s3_bucket_name        = module.s3.bucket_name
  s3_bucket_arn         = module.s3.bucket_arn
  s3_bucket_domain_name = module.s3.bucket_domain_name
}

module "scheduler" {
  source = "./modules/scheduler"

  project_name     = var.project_name
  environment      = var.environment
  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_name = module.ecs.service_name
  rds_instance_id  = module.rds.instance_id
}
