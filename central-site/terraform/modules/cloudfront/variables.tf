variable "project_name" {
  type = string
}

variable "environment" {
  type = string
}

variable "domain_name" {
  description = "Root domain (e.g. judi-expert.fr)"
  type        = string
}

variable "origin_domain" {
  description = "Origin domain name for CloudFront (must not be an IP)"
  type        = string
}

variable "route53_zone_id" {
  description = "Route 53 zone ID for ACM DNS validation"
  type        = string
}
