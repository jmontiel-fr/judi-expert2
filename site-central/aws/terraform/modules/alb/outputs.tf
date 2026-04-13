# ==============================================
# Outputs — Module ALB
# ==============================================

output "alb_arn" {
  description = "ARN de l'Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "Nom DNS de l'ALB"
  value       = aws_lb.main.dns_name
}

output "backend_target_group_arn" {
  description = "ARN du target group backend"
  value       = aws_lb_target_group.backend.arn
}

output "frontend_target_group_arn" {
  description = "ARN du target group frontend"
  value       = aws_lb_target_group.frontend.arn
}

output "http_listener_arn" {
  description = "ARN du listener HTTP"
  value       = aws_lb_listener.http.arn
}
