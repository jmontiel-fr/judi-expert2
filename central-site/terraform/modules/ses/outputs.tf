output "domain_identity_arn" {
  description = "ARN de l'identité SES du domaine"
  value       = aws_ses_domain_identity.main.arn
}

output "sender_email" {
  description = "Adresse email d'envoi"
  value       = "no-reply@${var.domain_name}"
}
