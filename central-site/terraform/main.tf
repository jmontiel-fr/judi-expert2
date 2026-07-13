# ==============================================
# Judi-Expert — Infrastructure AWS (Site Central)
# Architecture : CloudFront + Lightsail + RDS (~29 $/mois)
# Network: Lightsail ←VPC Peering→ VPC (RDS private)
# ==============================================

# --- DNS Zone (created first for ACM validation) ---
module "dns" {
  source = "./modules/dns"

  project_name = var.project_name
  environment  = var.environment
  domain_name  = var.domain_name
}

# --- VPC + Lightsail VPC Peering ---
module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
}

# --- RDS PostgreSQL (private, accessible via VPC peering) ---
module "rds" {
  source = "./modules/rds"

  project_name      = var.project_name
  environment       = var.environment
  db_instance_class = var.db_instance_class
  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = var.db_password
  vpc_id            = module.vpc.vpc_id
  subnet_ids        = module.vpc.subnet_ids

  depends_on = [module.vpc]
}

# --- SES (email sending for Cognito) ---
module "ses" {
  source = "./modules/ses"

  project_name    = var.project_name
  environment     = var.environment
  domain_name     = var.domain_name
  route53_zone_id = module.dns.zone_id
}

# --- Cognito ---
module "cognito" {
  source = "./modules/cognito"

  project_name              = var.project_name
  environment               = var.environment
  admin_email               = var.admin_email
  admin_temporary_password  = var.admin_temporary_password
  expert_email              = var.expert_email
  expert_temporary_password = var.expert_temporary_password
  domain_name               = var.domain_name
  ses_domain_identity_arn   = module.ses.domain_identity_arn

  depends_on = [module.ses]
}

# --- Lightsail Instance ---
module "lightsail" {
  source = "./modules/lightsail"

  project_name  = var.project_name
  environment   = var.environment
  aws_region    = var.aws_region
  instance_plan = var.lightsail_plan
  rds_endpoint  = module.rds.endpoint
  rds_db_name   = var.db_name
  rds_username  = var.db_username
  rds_password  = var.db_password
}

# --- CloudFront + ACM (uses DNS zone for cert validation) ---
module "cloudfront" {
  source = "./modules/cloudfront"

  providers = {
    aws           = aws
    aws.us_east_1 = aws.us_east_1
  }

  project_name    = var.project_name
  environment     = var.environment
  domain_name     = var.domain_name
  origin_domain   = "origin.${var.domain_name}"
  route53_zone_id = module.dns.zone_id
}

# --- Route 53 Records ---

# Origin record: origin.judi-expert.fr -> Lightsail IP (used by CloudFront)
resource "aws_route53_record" "origin" {
  zone_id = module.dns.zone_id
  name    = "origin.${var.domain_name}"
  type    = "A"
  ttl     = 300
  records = [module.lightsail.public_ip]
}

# Alias: www.judi-expert.fr -> CloudFront
resource "aws_route53_record" "www" {
  zone_id = module.dns.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"

  alias {
    name                   = module.cloudfront.domain_name
    zone_id                = module.cloudfront.hosted_zone_id
    evaluate_target_health = false
  }
}

# Alias: judi-expert.fr (apex) -> CloudFront
resource "aws_route53_record" "apex" {
  zone_id = module.dns.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = module.cloudfront.domain_name
    zone_id                = module.cloudfront.hosted_zone_id
    evaluate_target_health = false
  }
}

# Google Search Console (verification domaine) — optionnel
resource "aws_route53_record" "google_site_verification" {
  count = var.google_site_verification != "" ? 1 : 0

  zone_id = module.dns.zone_id
  name    = var.domain_name
  type    = "TXT"
  ttl     = 300
  records = [var.google_site_verification]
}

# --- Cron Abonnement (EventBridge + Lambda) ---
module "cron" {
  source = "./modules/cron"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region
  api_base_url = "https://origin.${var.domain_name}:8000"
}

# --- S3 Bucket (packages Site Client — eu-west-3) ---
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
}

# --- ECR (Docker registry — remains in eu-west-1) ---
module "ecr" {
  source = "./modules/ecr"

  providers = {
    aws = aws.eu_west_1
  }

  project_name = var.project_name
  environment  = var.environment
}

