output "endpoint" {
  description = "Endpoint de connexion RDS (host:port)"
  value       = aws_db_instance.main.endpoint
}

output "address" {
  description = "Adresse de l'instance RDS"
  value       = aws_db_instance.main.address
}

output "port" {
  description = "Port de l'instance RDS"
  value       = aws_db_instance.main.port
}

output "instance_id" {
  description = "Identifiant de l'instance RDS"
  value       = aws_db_instance.main.id
}

output "db_name" {
  description = "Nom de la base de données"
  value       = aws_db_instance.main.db_name
}
