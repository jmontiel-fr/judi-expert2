# ==============================================
# Judi-Expert — Infrastructure AWS (Site Central)
# Architecture : CloudFront + Lightsail + RDS (~29 $/mois)
# ==============================================

# --- DNS Zone (created first for ACM validation) ---
module "dns" {
  source = "./modules/dns"

  project_name = var.project_name
  environment  = var.environment
  domain_name  = var.domain_name
}

# --- RDS PostgreSQL ---
module "rds" {
  source = "./modules/rds"

  project_name      = var.project_name
  environment       = var.environment
  db_instance_class = var.db_instance_class
  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = var.db_password
}

# --- Cognito ---
module "cognito" {
  source = "./modules/cognito"

  project_name = var.project_name
  environment  = var.environment
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
