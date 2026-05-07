output "public_ip" {
  description = "Public IP of the Lightsail instance"
  value       = aws_lightsail_static_ip.main.ip_address
}

output "instance_name" {
  description = "Name of the Lightsail instance"
  value       = aws_lightsail_instance.main.name
}
