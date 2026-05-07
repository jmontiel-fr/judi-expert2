# ==============================================
# Judi-Expert — Terraform Variables (Production)
# Architecture: Lightsail + RDS (phase lancement)
# ==============================================

project_name = "judi-expert"
environment  = "production"
aws_region   = "eu-west-1"

# --- Lightsail ---
# Plans: nano_3_0 (512MB/$5), micro_3_0 (1GB/$10), small_3_0 (2GB/$12), medium_3_0 (4GB/$24)
lightsail_plan = "small_3_0"

# --- RDS ---
db_instance_class = "db.t4g.micro"
db_name           = "judi_expert"
db_username       = "judi_admin"
db_password       = "JudiExpert2026!Prod"

# --- DNS ---
domain_name = "judi-expert.fr"
