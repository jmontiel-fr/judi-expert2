# ==============================================
# Route 53 — Hosted Zone only
# DNS records are created after CloudFront
# ==============================================

resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}
